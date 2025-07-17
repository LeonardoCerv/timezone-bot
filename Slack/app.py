import os
import re
import json
import pytz
import threading
import subprocess
from datetime import datetime
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt.oauth import OAuthFlow
from slack_bolt.oauth.oauth_settings import OAuthSettings
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()

# File paths
USER_PREFS_PATH = '../shared/user_preferences.json'
SHARED_TIMEZONES_PATH = '../shared/timezones.json'
RESPONSE_MESSAGES_PATH = '../shared/response_messages.json'

# Load shared timezone config
timezone_config = {'aliases': {}, 'popular': []}
try:
    if os.path.exists(SHARED_TIMEZONES_PATH):
        with open(SHARED_TIMEZONES_PATH, 'r') as f:
            timezone_config = json.load(f)
except Exception as error:
    print(f'Failed to load timezone config: {error}')

# Load shared response messages
response_messages = {}
try:
    if os.path.exists(RESPONSE_MESSAGES_PATH):
        with open(RESPONSE_MESSAGES_PATH, 'r') as f:
            response_messages = json.load(f)
except Exception as error:
    print(f'Failed to load response messages: {error}')

# Format messages for Slack (convert **bold** to *bold*)
def format_for_slack(message):
    return message.replace('**', '*')

# Database functions
def init_user_prefs():
    if not os.path.exists(USER_PREFS_PATH):
        with open(USER_PREFS_PATH, 'w') as f:
            json.dump({'discord': {}, 'slack': {}, 'telegram': {}}, f, indent=2)

def read_user_prefs():
    try:
        if not os.path.exists(USER_PREFS_PATH):
            init_user_prefs()
        with open(USER_PREFS_PATH, 'r') as f:
            full_data = json.load(f)
            return {'users': full_data.get('slack', {})}
    except Exception as error:
        print(f'Error reading user preferences: {error}')
        return {'users': {}}

def write_user_prefs(data):
    try:
        # Read existing data first
        full_data = {'discord': {}, 'slack': {}, 'telegram': {}}
        if os.path.exists(USER_PREFS_PATH):
            with open(USER_PREFS_PATH, 'r') as f:
                full_data = json.load(f)
        
        # Update only the slack section
        full_data['slack'] = data.get('users', {})
        
        with open(USER_PREFS_PATH, 'w') as f:
            json.dump(full_data, f, indent=2)
        return True
    except Exception as error:
        print(f'Error writing user preferences: {error}')
        return False

# Timezone utilities
# Helper function to get display name for timezone
def get_timezone_display_name(timezone_id):
    # Check if we have a display name in the timezone config
    if timezone_config.get('display_names') and timezone_id in timezone_config['display_names']:
        return timezone_config['display_names'][timezone_id]
    
    # Fallback to timezone name
    try:
        tz = pytz.timezone(timezone_id)
        now = datetime.now(tz)
        return now.strftime('%Z')
    except:
        return timezone_id.split('/')[-1].upper()

def normalize_timezone(input_tz):
    if not input_tz:
        return None
    
    # Check aliases first
    alias = timezone_config['aliases'].get(input_tz.upper())
    if alias:
        return alias
    
    # Check if it's a valid pytz timezone
    try:
        pytz.timezone(input_tz)
        return input_tz
    except:
        pass
    
    # Handle UTC offset formats (UTC-5, UTC+3:30)
    offset_match = re.match(r'^(UTC)?([+-]\d{1,2}):?(\d{2})?$', input_tz, re.IGNORECASE)
    if offset_match:
        sign = '+' if offset_match.group(2).startswith('+') else '-'
        hours = abs(int(offset_match.group(2)))
        minutes = int(offset_match.group(3)) if offset_match.group(3) else 0
        
        if hours <= 14 and minutes <= 59:
            # Etc/GMT offsets are inverted
            return f"Etc/GMT{'-' if sign == '+' else '+'}{hours}"
    
    return None

def set_user_timezone(user_id, timezone_input):
    normalized_tz = normalize_timezone(timezone_input)
    if not normalized_tz:
        return False
    
    data = read_user_prefs()
    data['users'][user_id] = {
        'timezone': normalized_tz,
        'displayName': timezone_input,
        'lastUpdated': datetime.now().isoformat()
    }
    return write_user_prefs(data)

def get_user_timezone(user_id):
    data = read_user_prefs()
    return data.get('users', {}).get(user_id, {}).get('timezone')

# Time parsing and conversion
def extract_times(content):
    patterns = [
        # With timezone: "3:00 PM EST", "2 PM PST", "3 PM SGT"
        r'\b(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)\s*([A-Z]{2,4}|UTC[+-]\d{1,2}:?\d{0,2}|GMT[+-]\d{1,2}:?\d{0,2})\b',
        r'\b(\d{1,2})\s*(AM|PM|am|pm)\s*([A-Z]{2,4}|UTC[+-]\d{1,2}:?\d{0,2}|GMT[+-]\d{1,2}:?\d{0,2})\b',
        # 12-hour: "3:00 PM", "3 PM"
        r'\b(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)\b',
        r'\b(\d{1,2})\s*(AM|PM|am|pm)\b',
        # 24-hour: "15:30", "09:00"
        r'\b([01]?\d|2[0-3]):([0-5]\d)\b',
        # With context: "at 3pm"
        r'\b(at|around|by|before|after)\s+(\d{1,2}):?(\d{2})?\s*(AM|PM|am|pm)?\b'
    ]
    
    times = []
    spans = []
    
    for pattern in patterns:
        for match in re.finditer(pattern, content, re.IGNORECASE):
            start = match.start()
            end = match.end()
            
            # Skip overlapping matches
            overlaps = any(
                (start >= span['start'] and start < span['end']) or
                (end > span['start'] and end <= span['end']) or
                (start <= span['start'] and end >= span['end'])
                for span in spans
            )
            
            if not overlaps:
                times.append(match.group(0).strip())
                spans.append({'start': start, 'end': end})
    
    return sorted([t for t in times if len(t) >= 2 and not re.match(r'^\d{1,2}$', t.strip())], 
                 key=lambda x: content.find(x))

def parse_time(time_str, context_tz='UTC'):
    if not time_str:
        return None
    
    timezone = context_tz
    
    # Look for timezone in string - improved regex to catch more formats, excluding AM/PM
    tz_match = re.search(r'\b(?!AM|PM)([A-Z]{2,4}|UTC[+-]\d{1,2}:?\d{0,2}|GMT[+-]\d{1,2}:?\d{0,2})\b', time_str, re.IGNORECASE)
    if tz_match:
        tz_candidate = tz_match.group(1)
        # Double-check it's not AM/PM
        if tz_candidate.upper() not in ['AM', 'PM']:
            normalized_tz = normalize_timezone(tz_candidate)
            if normalized_tz:
                timezone = normalized_tz
    
    # Clean up time string
    clean_time = re.sub(r'\b(at|around|by|before|after)\s+', '', time_str, flags=re.IGNORECASE)
    # Be more careful about removing timezone - don't remove AM/PM
    clean_time = re.sub(r'\b(?!AM|PM)([A-Z]{2,4}|UTC[+-]\d{1,2}:?\d{0,2}|GMT[+-]\d{1,2}:?\d{0,2})\b', '', clean_time, flags=re.IGNORECASE).strip()
    
    try:
        # Parse different formats
        if re.match(r'^\d{1,2}:\d{2}\s*(AM|PM)$', clean_time, re.IGNORECASE):
            dt = datetime.strptime(clean_time.upper(), '%I:%M %p')
        elif re.match(r'^\d{1,2}\s+(AM|PM)$', clean_time, re.IGNORECASE):
            dt = datetime.strptime(clean_time.upper(), '%I %p')
        elif re.match(r'^\d{1,2}(AM|PM)$', clean_time, re.IGNORECASE):
            # Handle cases like "3pm" without space
            normalized = re.sub(r'(\d+)(AM|PM)', r'\1 \2', clean_time, flags=re.IGNORECASE)
            dt = datetime.strptime(normalized.upper(), '%I %p')
        elif re.match(r'^\d{1,2}:\d{2}$', clean_time):
            dt = datetime.strptime(clean_time, '%H:%M')
        else:
            # Try some additional formats as fallback
            formats = ['%I:%M:%S %p', '%H:%M:%S', '%I %p', '%H:%M']
            dt = None
            for fmt in formats:
                try:
                    dt = datetime.strptime(clean_time.upper(), fmt)
                    break
                except ValueError:
                    continue
            if dt is None:
                return None
        
        # Create timezone-aware datetime for today
        tz = pytz.timezone(timezone)
        today = datetime.now(tz).date()
        localized_dt = tz.localize(datetime.combine(today, dt.time()))
        
        return {'datetime': localized_dt, 'timezone': timezone}
    except:
        return None

def convert_times(content, target_timezone):
    found_times = extract_times(content)
    if not found_times:
        return []
    
    results = []
    
    for time_str in found_times:
        # Try to parse with timezone from string, fallback to UTC only if no TZ found
        parsed = parse_time(time_str)
        if parsed:
            target_tz = pytz.timezone(target_timezone)
            converted = parsed['datetime'].astimezone(target_tz)
            same_day = parsed['datetime'].date() == converted.date()
            
            # Format consistently with proper timezone abbreviations
            original_formatted = f"{parsed['datetime'].strftime('%I:%M%p').lstrip('0')} {get_timezone_display_name(parsed['timezone'])}"
            converted_formatted = f"{converted.strftime('%I:%M%p').lstrip('0')} {get_timezone_display_name(target_timezone)}"
            
            results.append({
                'original': original_formatted,
                'converted': converted_formatted,
                'date': converted.strftime('%A, %B %d'),
                'same_day': same_day
            })
    
    return results

# Token management
def load_team_tokens():
    """Load team tokens from JSON file"""
    tokens_file = 'team_tokens.json'
    if os.path.exists(tokens_file):
        try:
            with open(tokens_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def get_team_token(team_id):
    """Get access token for a specific team"""
    tokens = load_team_tokens()
    return tokens.get(team_id, {}).get('access_token')

# Slack app setup - use proper authorization flow with xoxe token support
def authorize(enterprise_id, team_id, user_id):
    """Authorize function that returns AuthorizeResult"""
    from slack_bolt.authorization import AuthorizeResult
    
    print(f"Authorizing team {team_id}, enterprise_id: {enterprise_id}")
    
    # Get token for team
    token = get_team_token(team_id)
    if not token:
        print(f"No token found for team {team_id}")
        return None
    
    # Get bot user ID from saved data
    tokens = load_team_tokens()
    team_data = tokens.get(team_id, {})
    bot_user_id = team_data.get('bot_user_id')
    
    print(f"Found token for team {team_id}, bot_user_id: {bot_user_id}")
    print(f"Token type: {token[:4] if token else 'None'}")
    
    # Return AuthorizeResult - this should work with xoxe tokens
    try:
        result = AuthorizeResult(
            enterprise_id=enterprise_id,
            team_id=team_id,
            user_id=user_id,
            bot_token=token,
            bot_id=None,
            bot_user_id=bot_user_id,
            user_token=None
        )
        print(f"Successfully created AuthorizeResult for team {team_id}")
        return result
    except Exception as e:
        print(f"Error creating AuthorizeResult for team {team_id}: {e}")
        import traceback
        traceback.print_exc()
        return None

app = App(
    authorize=authorize,
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
)

@app.event("app_installed")
def handle_app_installed(event, say, context):
    """Handle app installation event"""
    team_id = context.get("team_id")
    print(f"App installed for team {team_id}")
    # Token should already be saved by OAuth flow

@app.event("app_uninstalled")
def handle_app_uninstalled(event, context):
    """Handle app uninstallation event"""
    team_id = context.get("team_id")
    print(f"App uninstalled for team {team_id}")
    # Could remove token here if needed

@app.event("message")
def handle_message(event, say, context):
    try:
        if event.get("subtype") == "bot_message" or event.get("bot_id"):
            return
        
        team_id = context.get("team_id")
        print(f"Processing message from team {team_id}")
        
        text = event.get("text", "")
        user_id = event.get("user")
        
        user_timezone = get_user_timezone(user_id)
        if not user_timezone:
            return
        
        conversions = convert_times(text, user_timezone)
        if conversions:
            response = format_for_slack((response_messages.get('success', {}).get('conversion_header', "**Times in your timezone ({timezone})**\n\n")).replace('{timezone}', user_timezone))
            for conv in conversions:
                template = (response_messages.get('success', {}).get('conversion_line', "**{original}** → **{converted}**") 
                           if conv['same_day'] 
                           else response_messages.get('success', {}).get('conversion_line_with_date', "**{original}** → **{converted}** ({date})"))
                
                line = template.replace('{original}', conv['original']).replace('{converted}', conv['converted']).replace('{date}', conv.get('date', ''))
                response += f"{format_for_slack(line)}\n"
            
            say(response.strip())
    except Exception as e:
        print(f"Error handling message: {e}")
        import traceback
        traceback.print_exc()

@app.event("app_mention")
def handle_app_mention(event, say, context):
    try:
        team_id = context.get("team_id")
        print(f"Processing app mention from team {team_id}")
        
        text = event.get("text", "")
        user_id = event.get("user")
        
        user_timezone = get_user_timezone(user_id)
        if not user_timezone:
            say(format_for_slack(response_messages.get('errors', {}).get('no_timezone_set', "No timezone set. Use `/timezone EST` to set one")))
            return
        
        conversions = convert_times(text, user_timezone)
        if conversions:
            response = format_for_slack((response_messages.get('success', {}).get('conversion_header', "**Times in your timezone ({timezone})**\n\n")).replace('{timezone}', user_timezone))
            for conv in conversions:
                template = (response_messages.get('success', {}).get('conversion_line', "**{original}** → **{converted}**") 
                           if conv['same_day'] 
                           else response_messages.get('success', {}).get('conversion_line_with_date', "**{original}** → **{converted}** ({date})"))
                
                line = template.replace('{original}', conv['original']).replace('{converted}', conv['converted']).replace('{date}', conv.get('date', ''))
                response += f"{format_for_slack(line)}\n"
            
            say(response.strip())
        else:
            say(format_for_slack(response_messages.get('errors', {}).get('no_times_found', "*No times found. Use format: /convert 3:00PM EST*")))
    except Exception as e:
        print(f"Error handling app mention: {e}")
        import traceback
        traceback.print_exc()

@app.command("/timezone")
def set_timezone_command(ack, respond, command, context):
    ack()
    
    try:
        team_id = context.get("team_id")
        print(f"Processing /timezone command from team {team_id}")
    
        timezone_input = command['text'].strip()
        user_id = command['user_id']
        
        if not timezone_input:
            current_tz = get_user_timezone(user_id)
            respond(format_for_slack(
                (response_messages.get('commands', {}).get('timezone_current', "Your timezone: `{timezone}`\n\nSet with: `/timezone EST` or `/timezone America/New_York`"))
                .replace('{timezone}', current_tz or 'Not set')
            ))
            return
        
        if not normalize_timezone(timezone_input):
            respond(format_for_slack(response_messages.get('errors', {}).get('invalid_timezone', "*Invalid timezone. Use format: /convert 3:00PM EST*")))
            return
        
        success = set_user_timezone(user_id, timezone_input)
        
        if success:
            tz = pytz.timezone(normalize_timezone(timezone_input))
            current_time = datetime.now(tz)
            formatted_time = current_time.strftime('%I:%M %p %Z').lstrip('0')
            
            respond(format_for_slack(
                (response_messages.get('success', {}).get('timezone_set', "Timezone set to `{timezone}`\nCurrent time: **{time}**"))
                .replace('{timezone}', timezone_input)
                .replace('{time}', formatted_time)
            ))
        else:
            respond(format_for_slack(response_messages.get('errors', {}).get('failed_to_save', "Failed to save timezone")))
    
    except Exception as e:
        print(f"Error in /timezone command: {e}")
        respond("An error occurred while processing your request.")

@app.command("/convert")
def convert_time_command(ack, respond, command, context):
    ack()
    
    try:
        team_id = context.get("team_id")
        print(f"Processing /convert command from team {team_id}")
    
        text = command['text'].strip()
        user_id = command['user_id']
        
        if not text:
            respond(format_for_slack(
                response_messages.get('commands', {}).get('convert_usage', "Provide a time to convert:\n• `/convert 3:00PM EST`\n• `/convert 14:30 PST`\n• `/convert 4 PM` (assumes UTC)")
            ))
            return
        
        user_timezone = get_user_timezone(user_id)
        if not user_timezone:
            respond(format_for_slack(response_messages.get('errors', {}).get('no_timezone_set', "No timezone set. Use `/timezone EST` to set one")))
            return
        
        conversions = convert_times(text, user_timezone)
        
        # If no timezone specified, try assuming UTC
        if not conversions:
            found_times = extract_times(text)
            for time_str in found_times:
                parsed = parse_time(time_str, 'UTC')
                if parsed:
                    target_tz = pytz.timezone(user_timezone)
                    converted = parsed['datetime'].astimezone(target_tz)
                    same_day = parsed['datetime'].date() == converted.date()
                    
                    # Format consistently with proper timezone abbreviations
                    original_formatted = f"{time_str} UTC"
                    converted_formatted = f"{converted.strftime('%I:%M%p').lstrip('0')} {get_timezone_display_name(user_timezone)}"
                    
                    conversions.append({
                        'original': original_formatted,
                        'converted': converted_formatted,
                        'date': converted.strftime('%A, %B %d'),
                        'same_day': same_day
                    })
        
        if not conversions:
            respond(format_for_slack(response_messages.get('errors', {}).get('no_times_found', "*No times found. Use format: /convert 3:00PM EST*")))
            return
        
        response = format_for_slack((response_messages.get('success', {}).get('conversion_header', "**Times in your timezone ({timezone})**\n\n")).replace('{timezone}', user_timezone))
        for conv in conversions:
            template = (response_messages.get('success', {}).get('conversion_line', "**{original}** → **{converted}**") 
                       if conv['same_day'] 
                       else response_messages.get('success', {}).get('conversion_line_with_date', "**{original}** → **{converted}** ({date})"))
            
            line = template.replace('{original}', conv['original']).replace('{converted}', conv['converted']).replace('{date}', conv.get('date', ''))
            response += f"{format_for_slack(line)}\n"
        
        respond(response.strip())
    
    except Exception as e:
        print(f"Error in /convert command: {e}")
        respond("An error occurred while processing your request.")

@app.command("/mytimezone")
def show_timezone_command(ack, respond, command, context):
    ack()
    
    try:
        team_id = context.get("team_id")
        print(f"Processing /mytimezone command from team {team_id}")
        
        user_id = command['user_id']
        user_timezone = get_user_timezone(user_id)
        
        if not user_timezone:
            respond(format_for_slack(response_messages.get('errors', {}).get('no_timezone_set', "No timezone set. Use `/timezone EST` to set one")))
            return
        
        try:
            tz = pytz.timezone(user_timezone)
            current_time = datetime.now(tz)
            formatted_time = current_time.strftime('%I:%M %p %Z').lstrip('0')
            date_str = current_time.strftime('%A, %B %d, %Y')
            
            respond(format_for_slack(
                (response_messages.get('success', {}).get('mytimezone_display', "**Your timezone:** `{timezone}`\n**Current time:** {time}\n**Date:** {date}"))
                .replace('{timezone}', user_timezone)
                .replace('{time}', formatted_time)
                .replace('{date}', date_str)
            ))
        except:
            respond(format_for_slack((response_messages.get('success', {}).get('mytimezone_simple', "**Your timezone:** `{timezone}`")).replace('{timezone}', user_timezone)))
    
    except Exception as e:
        print(f"Error in /mytimezone command: {e}")
        respond("An error occurred while processing your request.")

@app.command("/help")
def help_command(ack, respond, command, context):
    ack()
    
    try:
        team_id = context.get("team_id")
        print(f"Processing /help command from team {team_id}")
    
        help_text = format_for_slack(response_messages.get('help', {}).get('content', """**Commands:**
/timezone <timezone> - Set your timezone
/time <time> - Convert a time
/mytimezone - Show your timezone
/help - Show this help

**Formats:**
• 4 PM EST - 12-hour with timezone
• 4:30 PM PST - 12-hour with minutes  
• 16:30 GMT - 24-hour format
• 14:00 UTC - 24-hour format

**Timezones:**
• EST, PST, GMT, UTC, etc.
• America/New_York, Europe/London
• UTC-5, UTC+3

**Auto-detection:**
I detect times in messages and convert them automatically."""))
        
        respond(help_text)
    
    except Exception as e:
        print(f"Error in /help command: {e}")
        respond("An error occurred while processing your request.")

@app.error
def global_error_handler(error, body, logger):
    logger.exception(f"Error: {error}")

def start_oauth_server():
    """Start the OAuth server in a separate process"""
    try:
        print("Starting OAuth server...")
        # Run the oauth_server.py as a subprocess
        subprocess.Popen(
            ["python", "oauth_server.py"],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        print("OAuth server started on http://localhost:8944")
        print("Install URL: http://localhost:8944/install")
    except Exception as e:
        print(f"Failed to start OAuth server: {e}")

# Flask app for handling Slack events
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """Handle Slack events"""
    return handler.handle(request)

@flask_app.route("/slack/install", methods=["GET"])
def install():
    """Redirect to OAuth server install page"""
    return f'<script>window.location.href="http://localhost:8944/install";</script>'

@flask_app.route("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "timezone-bot"}

@flask_app.route("/status")
def status():
    """Show bot status and installed teams"""
    tokens = load_team_tokens()
    
    team_list = []
    for team_id, data in tokens.items():
        team_list.append({
            'team_id': team_id,
            'bot_user_id': data.get('bot_user_id'),
            'has_token': bool(data.get('access_token'))
        })
    
    return {
        'installed_teams': len(tokens),
        'teams': team_list,
        'service': 'timezone-bot-main'
    }

if __name__ == "__main__":
    print("Starting Timezone Bot...")
    
    # Start OAuth server first
    start_oauth_server()
    
    print("Starting Web API server...")
    
    init_user_prefs()
    
    try:
        # Run the Flask app for handling Slack events
        flask_app.run(host='0.0.0.0', port=3000, debug=True)
    except KeyboardInterrupt:
        print("\nBot stopped")
    except Exception as e:
        print(f"Error starting bot: {e}")
