import os
import re
import json
import pytz
import threading
import requests
import time
from datetime import datetime
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, redirect, render_template_string
from dotenv import load_dotenv

load_dotenv()

SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
SLACK_CLIENT_ID = os.environ.get("SLACK_CLIENT_ID")
SLACK_CLIENT_SECRET = os.environ.get("SLACK_CLIENT_SECRET")
SLACK_REDIRECT_URI = os.environ.get("SLACK_REDIRECT_URI", "https://slackbot.leonardocerv.hackclub.app/oauth")

USER_PREFS_PATH = '../shared/user_preferences.json'
SHARED_TIMEZONES_PATH = '../shared/timezones.json'

timezone_config = {'aliases': {}, 'popular': []}
if os.path.exists(SHARED_TIMEZONES_PATH):
    try:
        with open(SHARED_TIMEZONES_PATH, 'r') as f:
            timezone_config = json.load(f)
    except:
        pass

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
    except:
        return {'users': {}}

def write_user_prefs(data):
    try:
        full_data = {'discord': {}, 'slack': {}, 'telegram': {}}
        if os.path.exists(USER_PREFS_PATH):
            with open(USER_PREFS_PATH, 'r') as f:
                full_data = json.load(f)
        
        full_data['slack'] = data.get('users', {})
        
        with open(USER_PREFS_PATH, 'w') as f:
            json.dump(full_data, f, indent=2)
        return True
    except:
        return False

def get_timezone_display_name(timezone_id):
    if timezone_config.get('display_names') and timezone_id in timezone_config['display_names']:
        return timezone_config['display_names'][timezone_id]
    
    try:
        tz = pytz.timezone(timezone_id)
        now = datetime.now(tz)
        return now.strftime('%Z')
    except:
        return timezone_id.split('/')[-1].upper()

def normalize_timezone(input_tz):
    if not input_tz:
        return None
    
    alias = timezone_config['aliases'].get(input_tz.upper())
    if alias:
        return alias
    
    try:
        pytz.timezone(input_tz)
        return input_tz
    except:
        pass
    
    offset_match = re.match(r'^(UTC)?([+-]\d{1,2}):?(\d{2})?$', input_tz, re.IGNORECASE)
    if offset_match:
        sign = '+' if offset_match.group(2).startswith('+') else '-'
        hours = abs(int(offset_match.group(2)))
        minutes = int(offset_match.group(3)) if offset_match.group(3) else 0
        
        if hours <= 14 and minutes <= 59:
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
    tokens_file = 'team_tokens.json'
    if os.path.exists(tokens_file):
        try:
            with open(tokens_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def get_team_token(team_id):
    """Get access token for a specific team"""
    tokens = load_team_tokens()
    return tokens.get(team_id, {}).get('access_token')

def save_team_token(team_id, access_token, bot_user_id, team_data=None):
    tokens_file = 'team_tokens.json'
    
    try:
        tokens = {}
        if os.path.exists(tokens_file):
            try:
                with open(tokens_file, 'r') as f:
                    tokens = json.load(f)
            except:
                tokens = {}
        
        token_data = {
            'access_token': access_token,
            'bot_user_id': bot_user_id,
            'team_id': team_id,
            'installed_at': datetime.now().isoformat()
        }
        
        if team_data:
            token_data.update(team_data)
        
        tokens[team_id] = token_data
        
        with open(tokens_file, 'w') as f:
            json.dump(tokens, f, indent=2)
            
        print(f"Saved token for team {team_id}")
        return True
        
    except Exception as e:
        print(f"Error saving team token: {e}")
        return False

# Socket mode app setup with multi-workspace support
def authorize(enterprise_id, team_id, user_id):
    """Authorize function that loads bot tokens from team_tokens.json"""
    from slack_bolt.authorization import AuthorizeResult
    
    # Load team tokens from file
    tokens = load_team_tokens()
    team_data = tokens.get(team_id, {})
    bot_token = team_data.get('access_token')
    bot_user_id = team_data.get('bot_user_id')
    
    if not bot_token or not bot_user_id:
        return None
    
    return AuthorizeResult(
        enterprise_id=enterprise_id,
        team_id=team_id,
        user_id=user_id,
        bot_token=bot_token,
        bot_user_id=bot_user_id
    )

app = App(
    authorize=authorize,
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    process_before_response=True
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
def handle_message(event, say):
    try:
        if event.get("subtype") == "bot_message" or event.get("bot_id"):
            return
        
        user_id = event.get("user")
        text = event.get("text", "")
        
        user_timezone = get_user_timezone(user_id)
        if not user_timezone:
            return
        
        conversions = convert_times(text, user_timezone)
        if conversions:
            response = f"*Times in your timezone ({user_timezone})*\n\n"
            for conv in conversions:
                if conv['same_day']:
                    response += f"*{conv['original']}* → *{conv['converted']}*\n"
                else:
                    response += f"*{conv['original']}* → *{conv['converted']}* ({conv['date']})\n"
            
            say(response.strip())
    except Exception as e:
        print(f"Error handling message: {e}")

@app.event("app_mention")
def handle_app_mention(event, say):
    try:
        text = event.get("text", "")
        user_id = event.get("user")
        
        user_timezone = get_user_timezone(user_id)
        if not user_timezone:
            say("No timezone set. Use `/timezone EST` to set one")
            return
        
        conversions = convert_times(text, user_timezone)
        if conversions:
            response = f"*Times in your timezone ({user_timezone})*\n\n"
            for conv in conversions:
                if conv['same_day']:
                    response += f"*{conv['original']}* → *{conv['converted']}*\n"
                else:
                    response += f"*{conv['original']}* → *{conv['converted']}* ({conv['date']})\n"
            
            say(response.strip())
        else:
            say("No times found. Use format: `/convert 3:00PM EST`")
    except Exception as e:
        print(f"Error handling app mention: {e}")

@app.command("/timezone")
def set_timezone_command(ack, respond, command):
    ack()
    
    try:
        timezone_input = command['text'].strip()
        user_id = command['user_id']
        
        if not timezone_input:
            current_tz = get_user_timezone(user_id)
            respond(f"Your timezone: `{current_tz or 'Not set'}`\n\nSet with: `/timezone EST` or `/timezone America/New_York`")
            return
        
        if not normalize_timezone(timezone_input):
            respond("Invalid timezone. Try `/timezone EST` or `/timezone America/New_York`")
            return
        
        success = set_user_timezone(user_id, timezone_input)
        
        if success:
            tz = pytz.timezone(normalize_timezone(timezone_input))
            current_time = datetime.now(tz)
            formatted_time = current_time.strftime('%I:%M %p %Z').lstrip('0')
            
            respond(f"Timezone set to `{timezone_input}`\nCurrent time: *{formatted_time}*")
        else:
            respond("Failed to save timezone")
    
    except Exception as e:
        print(f"Error in /timezone command: {e}")
        respond("An error occurred while processing your request.")

@app.command("/convert")
def convert_time_command(ack, respond, command):
    ack()
    
    try:
        text = command['text'].strip()
        user_id = command['user_id']
        
        if not text:
            respond("Provide a time to convert:\n• `/convert 3:00PM EST`\n• `/convert 14:30 PST`\n• `/convert 4 PM` (assumes UTC)")
            return
        
        user_timezone = get_user_timezone(user_id)
        if not user_timezone:
            respond("No timezone set. Use `/timezone EST` to set one")
            return
        
        conversions = convert_times(text, user_timezone)
        
        if not conversions:
            found_times = extract_times(text)
            for time_str in found_times:
                parsed = parse_time(time_str, 'UTC')
                if parsed:
                    target_tz = pytz.timezone(user_timezone)
                    converted = parsed['datetime'].astimezone(target_tz)
                    same_day = parsed['datetime'].date() == converted.date()
                    
                    original_formatted = f"{time_str} UTC"
                    converted_formatted = f"{converted.strftime('%I:%M%p').lstrip('0')} {get_timezone_display_name(user_timezone)}"
                    
                    conversions.append({
                        'original': original_formatted,
                        'converted': converted_formatted,
                        'date': converted.strftime('%A, %B %d'),
                        'same_day': same_day
                    })
        
        if not conversions:
            respond("No times found. Use format: `/convert 3:00PM EST`")
            return
        
        response = f"*Times in your timezone ({user_timezone})*\n\n"
        for conv in conversions:
            if conv['same_day']:
                response += f"*{conv['original']}* → *{conv['converted']}*\n"
            else:
                response += f"*{conv['original']}* → *{conv['converted']}* ({conv['date']})\n"
        
        respond(response.strip())
    
    except Exception as e:
        print(f"Error in /convert command: {e}")
        respond("An error occurred while processing your request.")

@app.command("/mytimezone")
def show_timezone_command(ack, respond, command):
    ack()
    
    try:
        user_id = command['user_id']
        user_timezone = get_user_timezone(user_id)
        
        if not user_timezone:
            respond("No timezone set. Use `/timezone EST` to set one")
            return
        
        try:
            tz = pytz.timezone(user_timezone)
            current_time = datetime.now(tz)
            formatted_time = current_time.strftime('%I:%M %p %Z').lstrip('0')
            date_str = current_time.strftime('%A, %B %d, %Y')
            
            respond(f"*Your timezone:* `{user_timezone}`\n*Current time:* {formatted_time}\n*Date:* {date_str}")
        except:
            respond(f"*Your timezone:* `{user_timezone}`")
    
    except Exception as e:
        print(f"Error in /mytimezone command: {e}")
        respond("An error occurred while processing your request.")

@app.command("/help")
def help_command(ack, respond, command):
    ack()
    
    try:
        help_text = """*Commands:*
/timezone <timezone> - Set your timezone
/convert <time> - Convert a time
/mytimezone - Show your timezone
/help - Show this help

*Formats:*
• 4 PM EST - 12-hour with timezone
• 4:30 PM PST - 12-hour with minutes  
• 16:30 GMT - 24-hour format
• 14:00 UTC - 24-hour format

*Timezones:*
• EST, PST, GMT, UTC, etc.
• America/New_York, Europe/London
• UTC-5, UTC+3

*Auto-detection:*
I detect times in messages and convert them automatically."""
        
        respond(help_text)
    
    except Exception as e:
        print(f"Error in /help command: {e}")
        respond("An error occurred while processing your request.")

@app.error
def global_error_handler(error, body, logger):
    logger.exception(f"Error: {error}")



# Flask app for handling Slack events
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

# Test website template
TEST_WEBSITE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Timezone Bot - Test Website</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
            margin: 0;
            padding: 0;
            background: #f8f8f8;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: #fff;
            border: 1px solid #e5e5e5;
            padding: 3rem 2rem;
            max-width: 600px;
            margin: 2rem;
        }
        h1 {
            color: #1a1a1a;
            margin-bottom: 1rem;
            font-size: 2rem;
            font-weight: 400;
            letter-spacing: -0.025em;
        }
        .description {
            color: #666;
            line-height: 1.5;
            margin-bottom: 2rem;
            font-size: 0.875rem;
        }
        .status {
            background: #1a1a1a;
            color: #e5e5e5;
            padding: 1.5rem;
            margin: 2rem 0;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace;
        }
        .status h3 {
            color: #e5e5e5;
            margin-top: 0;
            margin-bottom: 1rem;
            font-weight: 500;
            font-size: 1rem;
        }
        .status ul {
            margin: 0;
            padding-left: 1rem;
            list-style: none;
        }
        .status li {
            margin-bottom: 0.5rem;
            color: #e5e5e5;
            font-size: 0.875rem;
        }
        .link {
            display: inline-block;
            color: #1a1a1a;
            text-decoration: none;
            font-size: 0.875rem;
            border-bottom: 1px solid #1a1a1a;
            padding-bottom: 1px;
            margin-top: 1rem;
        }
        .link:hover {
            opacity: 0.7;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Timezone Bot</h1>
        <p class="description">Slack bot for automatic timezone conversion</p>
        
        <div class="status">
            <h3>Service Status</h3>
            <ul>
                <li>✅ Main service: Running on port 8944</li>
                <li>✅ Event handler: Ready to receive Slack events</li>
                <li>✅ Commands: /timezone, /convert, /mytimezone, /help</li>
            </ul>
        </div>
        
        <p>This is a test website to verify the Slack bot's web interface is working correctly.</p>
        
        <a href="/status" class="link">Check bot status →</a>
        <a href="/health" class="link">Health check →</a>
    </div>
</body>
</html>
"""

# OAuth templates
INSTALL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>install timezone bot</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
            margin: 0;
            padding: 0;
            background: #f8f8f8;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: #fff;
            border: 1px solid #e5e5e5;
            padding: 3rem 2rem;
            max-width: 600px;
            margin: 2rem;
        }
        h1 {
            color: #1a1a1a;
            margin-bottom: 1rem;
            font-size: 2rem;
            font-weight: 400;
            letter-spacing: -0.025em;
        }
        .description {
            color: #666;
            line-height: 1.5;
            margin-bottom: 2rem;
            font-size: 0.875rem;
        }
        .features {
            background: #1a1a1a;
            color: #e5e5e5;
            padding: 1.5rem;
            margin: 2rem 0;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace;
        }
        .features h3 {
            color: #e5e5e5;
            margin-top: 0;
            margin-bottom: 1rem;
            font-weight: 500;
            font-size: 1rem;
        }
        .features ul {
            margin: 0;
            padding-left: 1rem;
            list-style: none;
        }
        .features li {
            margin-bottom: 0.75rem;
            color: #e5e5e5;
            font-size: 0.875rem;
            line-height: 1.4;
        }
        .install-button {
            display: inline-block;
            color: #1a1a1a;
            text-decoration: none;
            font-size: 0.875rem;
            border-bottom: 1px solid #1a1a1a;
            padding-bottom: 1px;
            margin-top: 1.5rem;
        }
        .install-button:hover {
            opacity: 0.7;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>timezone bot</h1>
        <p class="description">automatically convert times to your preferred timezone in slack conversations</p>
        
        <div class="features">
            <h3>features</h3>
            <ul>
                <li>automatic time conversion: detects times in messages and shows them in your timezone</li>
                <li>personal timezone settings: set your preferred timezone once and forget about it</li>
                <li>multiple format support: works with 12-hour, 24-hour, and timezone-specific formats</li>
                <li>simple commands: easy slash commands to manage your timezone preferences</li>
                <li>cross-platform: works seamlessly across all slack clients</li>
            </ul>
        </div>
        
        <p>ready to never miss a meeting due to timezone confusion again?</p>
        
        <a href="https://slack.com/oauth/v2/authorize?client_id={{ client_id }}&scope=app_mentions:read,channels:history,chat:write,commands&redirect_uri={{ redirect_uri }}&state=install" class="install-button">
            add to slack →
        </a>
    </div>
</body>
</html>
"""

SUCCESS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>installation successful</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
            margin: 0;
            padding: 0;
            background: #f8f8f8;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: #fff;
            border: 1px solid #e5e5e5;
            padding: 3rem 2rem;
            max-width: 500px;
            margin: 2rem;
        }
        h1 {
            color: #1a1a1a;
            margin-bottom: 1rem;
            font-size: 1.5rem;
            font-weight: 500;
            letter-spacing: -0.015em;
        }
        p {
            color: #666;
            line-height: 1.5;
            margin-bottom: 1rem;
            font-size: 0.875rem;
        }
        .commands {
            background: #1a1a1a;
            color: #e5e5e5;
            padding: 1.5rem;
            margin: 1.5rem 0;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace;
        }
        .commands h3 {
            color: #e5e5e5;
            margin-top: 0;
            margin-bottom: 1rem;
            font-weight: 500;
            font-size: 1rem;
        }
        .commands ul {
            margin: 0;
            padding-left: 1rem;
            list-style: none;
        }
        .commands li {
            margin-bottom: 0.5rem;
            color: #e5e5e5;
            font-size: 0.875rem;
        }
        .back-link {
            display: inline-block;
            color: #1a1a1a;
            text-decoration: none;
            font-size: 0.875rem;
            border-bottom: 1px solid #1a1a1a;
            padding-bottom: 1px;
            margin-top: 1rem;
        }
        .back-link:hover {
            opacity: 0.7;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>installation successful</h1>
        <p>timezone bot has been added to your slack workspace.</p>
        
        <div class="commands">
            <h3>available commands:</h3>
            <ul>
                <li>/timezone set EST</li>
                <li>/timezone show</li>
                <li>/timezone help</li>
            </ul>
        </div>
        
        <p>the bot will automatically detect and convert times mentioned in messages to your preferred timezone.</p>
        
        <a href="slack://open" class="back-link">back to slack →</a>
    </div>
</body>
</html>
"""

ERROR_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>installation error</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
            margin: 0;
            padding: 0;
            background: #f8f8f8;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: #fff;
            border: 1px solid #e5e5e5;
            padding: 3rem 2rem;
            max-width: 500px;
            margin: 2rem;
        }
        h1 {
            color: #1a1a1a;
            margin-bottom: 1rem;
            font-size: 1.5rem;
            font-weight: 500;
            letter-spacing: -0.015em;
        }
        p {
            color: #666;
            line-height: 1.5;
            margin-bottom: 1rem;
            font-size: 0.875rem;
        }
        .try-again {
            display: inline-block;
            color: #1a1a1a;
            text-decoration: none;
            font-size: 0.875rem;
            border-bottom: 1px solid #1a1a1a;
            padding-bottom: 1px;
            margin-top: 1rem;
        }
        .try-again:hover {
            opacity: 0.7;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>installation failed</h1>
        <p>something went wrong during the installation process.</p>
        <p>please try installing the app again, or contact support if the problem persists.</p>
        
        <a href="/install" class="try-again">try again →</a>
    </div>
</body>
</html>
"""

@flask_app.route("/", methods=["GET", "POST"])
def root():
    """Root endpoint - shows test website on GET, handles Slack events on POST"""
    if request.method == "GET":
        return TEST_WEBSITE
    elif request.method == "POST":
        # Handle Slack events
        try:
            return handler.handle(request)
        except Exception as e:
            print(f"Error handling Slack event: {e}")
            import traceback
            traceback.print_exc()
            return "", 500

@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """Handle Slack events (backup endpoint)"""
    return handler.handle(request)

@flask_app.route("/status")
def status():
    """Status endpoint"""
    tokens = load_team_tokens()
    return {
        "status": "running",
        "mode": "socket" if SLACK_APP_TOKEN else "http",
        "oauth_enabled": bool(SLACK_CLIENT_ID and SLACK_CLIENT_SECRET),
        "installed_workspaces": len(tokens),
        "workspaces": [{"team_id": tid, "team_name": data.get("team_name", "Unknown")} for tid, data in tokens.items()]
    }

@flask_app.route("/health")
def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "timezone-bot-unified", "port": 8944, "oauth_enabled": True}



@flask_app.route('/install')
def install():
    """Show the installation page with Add to Slack button"""
    return render_template_string(
        INSTALL_TEMPLATE,
        client_id=SLACK_CLIENT_ID,
        redirect_uri=SLACK_REDIRECT_URI
    )

@flask_app.route('/oauth')
def oauth_callback():
    """Handle the OAuth callback from Slack"""
    try:
        # Get the authorization code from Slack
        code = request.args.get('code')
        error = request.args.get('error')
        state = request.args.get('state')
        
        # Handle OAuth errors
        if error:
            return redirect('/error')
        
        if not code:
            return redirect('/error')
        
        # Check the state parameter if you sent one along with your initial user redirect
        # If it doesn't match what you sent, consider the authorization a forgery
        if state != 'install':
            return redirect('/error')
        
        # Exchange the code for an access token
        token_response = requests.post('https://slack.com/api/oauth.v2.access', data={
            'client_id': SLACK_CLIENT_ID,
            'client_secret': SLACK_CLIENT_SECRET,
            'code': code,
            'redirect_uri': SLACK_REDIRECT_URI
        })
        
        if token_response.status_code != 200:
            return redirect('/error')
        
        token_data = token_response.json()
        
        # Check if the OAuth response is successful
        if not token_data.get('ok'):
            return redirect('/error')
        
        # Extract team information
        team_info = token_data.get('team', {})
        team_id = team_info.get('id')
        team_name = team_info.get('name', 'Unknown Team')
        
        # Get bot token and user ID
        bot_token = token_data.get('access_token')
        bot_user_id = token_data.get('bot_user_id')
        
        # Validate we have required data
        if not all([team_id, bot_token, bot_user_id]):
            return redirect('/error')
        
        # Save the team's token
        additional_data = {
            'team_name': team_name,
            'app_id': token_data.get('app_id'),
            'scope': token_data.get('scope', '')
        }
        
        if not save_team_token(team_id, bot_token, bot_user_id, additional_data):
            return redirect('/error')
        
        return redirect('/thanks')
        
    except Exception as e:
        print(f"OAuth callback error: {e}")
        return redirect('/error')

@flask_app.route('/thanks')
def thanks():
    """Show success page after successful installation"""
    return render_template_string(SUCCESS_TEMPLATE)

@flask_app.route('/error')
def error():
    """Show error page if installation fails"""
    return render_template_string(ERROR_TEMPLATE)

def validate_environment():
    """Validate required environment variables"""
    # For socket mode operation
    socket_vars = ['SLACK_APP_TOKEN', 'SLACK_SIGNING_SECRET']
    # For OAuth installation
    oauth_vars = ['SLACK_CLIENT_ID', 'SLACK_CLIENT_SECRET', 'SLACK_SIGNING_SECRET']
    
    missing_socket_vars = [var for var in socket_vars if not os.environ.get(var)]
    missing_oauth_vars = [var for var in oauth_vars if not os.environ.get(var)]
    
    if missing_socket_vars and missing_oauth_vars:
        print(f"Error: Missing environment variables for both modes:")
        print(f"  Socket mode: {', '.join(missing_socket_vars)}")
        print(f"  OAuth mode: {', '.join(missing_oauth_vars)}")
        return False
    
    return True

if __name__ == "__main__":
    print("Starting Timezone Bot...")
    
    # Validate environment
    if not validate_environment():
        exit(1)
    
    init_user_prefs()
    
    if SLACK_APP_TOKEN:
        print("Socket Mode: Bot will connect directly to Slack via WebSocket")
        print("Bot tokens will be loaded from team_tokens.json for each workspace")
        print("Flask Server: Running on port 8944 for OAuth installation")
        print("Install URL: https://slackbot.leonardocerv.hackclub.app/install")
        print("Status URL: https://slackbot.leonardocerv.hackclub.app/status")
        
        # Run Flask server in background thread for OAuth only
        import threading
        def run_flask():
            flask_app.run(host='0.0.0.0', port=8944, debug=False, use_reloader=False)
        
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        # Run Socket Mode as main process
        try:
            handler = SocketModeHandler(app, SLACK_APP_TOKEN)
            handler.start()
        except KeyboardInterrupt:
            print("\nBot stopped")
        except Exception as e:
            print(f"Socket mode error: {e}")
    else:
        print("Socket Mode: Disabled (missing SLACK_APP_TOKEN)")
        print("Flask Server: Running on port 8944 for OAuth installation only")
        print("Install URL: https://slackbot.leonardocerv.hackclub.app/install")
        
        try:
            flask_app.run(host='0.0.0.0', port=8944, debug=False)
        except KeyboardInterrupt:
            print("\nBot stopped")
        except Exception as e:
            print(f"Error starting Flask server: {e}")
