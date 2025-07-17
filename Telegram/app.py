import os
import re
import json
import pytz
import subprocess
from datetime import datetime
import telebot
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
            return {'users': full_data.get('telegram', {})}
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
        
        # Update only the telegram section
        full_data['telegram'] = data.get('users', {})
        
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
    data['users'][str(user_id)] = {
        'timezone': normalized_tz,
        'displayName': timezone_input,
        'lastUpdated': datetime.now().isoformat()
    }
    return write_user_prefs(data)

def get_user_timezone(user_id):
    data = read_user_prefs()
    return data.get('users', {}).get(str(user_id), {}).get('timezone')

def is_user_authenticated(user_id):
    """Check if user is authenticated through web interface"""
    users_file = 'telegram_users.json'
    if os.path.exists(users_file):
        try:
            with open(users_file, 'r') as f:
                users = json.load(f)
                return str(user_id) in users and users[str(user_id)].get('authenticated', False)
        except json.JSONDecodeError:
            return False
    return False

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

# Bot setup
bot = telebot.TeleBot(os.environ.get('TELEGRAM_BOT_TOKEN'))

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_timezone = get_user_timezone(user_id)
    is_authenticated = is_user_authenticated(user_id)
    
    auth_status = "✅ Authenticated" if is_authenticated else "❌ Not authenticated"
    auth_info = "" if is_authenticated else "\n\n**🔗 Link your account:** Visit https://telegrambot.leonardocerv.hackclub.app to authenticate and enable full features."
    
    welcome_text = f"""**Welcome to Timezone Bot!**

I automatically convert times between timezones.

**Your timezone:** `{user_timezone or 'Not set'}`
**Authentication:** {auth_status}{auth_info}

**Commands:**
/timezone EST - Set your timezone
/convert "3:00PM EST" - Convert a time  
/mytimezone - Show your timezone
/help - Show help

**Example:**
Send "Meeting at 3:00PM EST" and I'll convert it to your timezone."""
    
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = """**Commands**:
• `/timezone <timezone>` - Set your timezone
• `/convert <time>` - Convert a time
• `/mytimezone` - Show your timezone
• `/help` - Show this help

**Formats**:
• `4 PM EST` - 12-hour with timezone
• `4:30 PM PST` - 12-hour with minutes  
• `16:30 GMT` - 24-hour format
• `14:00 UTC` - 24-hour format

**Timezones**:
• `EST`, `PST`, `GMT`, `UTC`, etc.
• `America/New_York`, `Europe/London`
• `UTC-5`, `UTC+3`

**Auto-detection**:
I detect times in messages and convert them automatically."""
    
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['timezone'])
def handle_timezone(message):
    user_id = message.from_user.id
    command_parts = message.text.split()
    
    if len(command_parts) == 1:
        current_tz = get_user_timezone(user_id)
        bot.reply_to(message,
            (response_messages.get('commands', {}).get('timezone_current', "Your timezone: `{timezone}`\n\nSet with: `/timezone EST` or `/timezone America/New_York`"))
            .replace('{timezone}', current_tz or 'Not set'),
            parse_mode="Markdown"
        )
        return
    
    timezone_input = ' '.join(command_parts[1:])
    
    if not normalize_timezone(timezone_input):
        bot.reply_to(message,
            response_messages.get('errors', {}).get('invalid_timezone', "*Invalid timezone. Use format: /convert 3:00PM EST*"),
            parse_mode="Markdown"
        )
        return
    
    success = set_user_timezone(user_id, timezone_input)
    
    if success:
        tz = pytz.timezone(normalize_timezone(timezone_input))
        current_time = datetime.now(tz)
        formatted_time = current_time.strftime('%I:%M %p %Z').lstrip('0')
        
        bot.reply_to(message,
            (response_messages.get('success', {}).get('timezone_set', "Timezone set to `{timezone}`\nCurrent time: **{time}**"))
            .replace('{timezone}', timezone_input)
            .replace('{time}', formatted_time),
            parse_mode="Markdown"
        )
    else:
        bot.reply_to(message, response_messages.get('errors', {}).get('failed_to_save', "Failed to save timezone"), parse_mode="Markdown")

@bot.message_handler(commands=['convert'])
def handle_convert(message):
    user_id = message.from_user.id
    command_parts = message.text.split(maxsplit=1)
    
    if len(command_parts) == 1:
        bot.reply_to(message,
            response_messages.get('commands', {}).get('convert_usage', "Provide a time to convert:\n• `/convert 3:00PM EST`\n• `/convert 14:30 PST`\n• `/convert 4 PM` (assumes UTC)"),
            parse_mode="Markdown"
        )
        return
    
    time_text = command_parts[1]
    user_timezone = get_user_timezone(user_id)
    
    if not user_timezone:
        bot.reply_to(message, response_messages.get('errors', {}).get('no_timezone_set', "No timezone set. Use `/timezone EST` to set one"), parse_mode="Markdown")
        return
    
    conversions = convert_times(time_text, user_timezone)
    
    # If no timezone specified, try assuming UTC
    if not conversions:
        found_times = extract_times(time_text)
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
    
    if conversions:
        response = (response_messages.get('success', {}).get('conversion_header', "**Times in your timezone ({timezone})**\n\n")).replace('{timezone}', user_timezone)
        for conv in conversions:
            template = (response_messages.get('success', {}).get('conversion_line', "**{original}** → **{converted}**") 
                       if conv['same_day'] 
                       else response_messages.get('success', {}).get('conversion_line_with_date', "**{original}** → **{converted}** ({date})"))
            
            line = template.replace('{original}', conv['original']).replace('{converted}', conv['converted']).replace('{date}', conv.get('date', ''))
            response += f"{line}\n"
        
        bot.reply_to(message, response.strip(), parse_mode="Markdown")
    else:
        bot.reply_to(message,
            response_messages.get('errors', {}).get('no_times_found', "*No times found. Use format: /convert 3:00PM EST*"),
            parse_mode="Markdown"
        )

@bot.message_handler(commands=['mytimezone'])
def handle_mytimezone(message):
    user_id = message.from_user.id
    user_timezone = get_user_timezone(user_id)
    
    if not user_timezone:
        bot.reply_to(message, response_messages.get('errors', {}).get('no_timezone_set', "No timezone set. Use `/timezone EST` to set one"), parse_mode="Markdown")
        return
    
    try:
        tz = pytz.timezone(user_timezone)
        current_time = datetime.now(tz)
        formatted_time = current_time.strftime('%I:%M %p %Z').lstrip('0')
        date_str = current_time.strftime('%A, %B %d, %Y')
        
        bot.reply_to(message,
            (response_messages.get('success', {}).get('mytimezone_display', "**Your timezone:** `{timezone}`\n**Current time:** {time}\n**Date:** {date}"))
            .replace('{timezone}', user_timezone)
            .replace('{time}', formatted_time)
            .replace('{date}', date_str),
            parse_mode="Markdown"
        )
    except:
        bot.reply_to(message, (response_messages.get('success', {}).get('mytimezone_simple', "**Your timezone:** `{timezone}`")).replace('{timezone}', user_timezone), parse_mode="Markdown")

# Handle regular messages for auto-detection
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if not message.text or message.text.startswith('/'):
        return
    
    user_id = message.from_user.id
    user_timezone = get_user_timezone(user_id)
    
    if not user_timezone:
        return
    
    conversions = convert_times(message.text, user_timezone)
    
    if conversions:
        response = (response_messages.get('success', {}).get('conversion_header', "**Times in your timezone ({timezone})**\n\n")).replace('{timezone}', user_timezone)
        for conv in conversions:
            template = (response_messages.get('success', {}).get('conversion_line', "**{original}** → **{converted}**") 
                       if conv['same_day'] 
                       else response_messages.get('success', {}).get('conversion_line_with_date', "**{original}** → **{converted}** ({date})"))
            
            line = template.replace('{original}', conv['original']).replace('{converted}', conv['converted']).replace('{date}', conv.get('date', ''))
            response += f"{line}\n"
        
        bot.reply_to(message, response.strip(), parse_mode="Markdown")

def start_web_server():
    """Start the web server in a separate process"""
    try:
        print("Starting web server...")
        # Use sys.executable to get the current Python interpreter
        import sys
        subprocess.Popen(
            [sys.executable, "web_server.py"],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        print("Web server started")
        print("Install URL: https://telegrambot.leonardocerv.hackclub.app")
    except Exception as e:
        print(f"Failed to start web server: {e}")

if __name__ == '__main__':
    print("Starting Timezone Bot...")
    print("Commands: /timezone EST, /convert '3:00PM EST', /mytimezone, /help")
    
    # Check if bot token is set
    if not os.environ.get('TELEGRAM_BOT_TOKEN'):
        print("Error: TELEGRAM_BOT_TOKEN is not set in environment variables")
        exit(1)
    
    # Start web server first
    start_web_server()
    
    init_user_prefs()
    
    # Start bot with error handling and restart mechanism
    import time
    import requests
    from telebot.apihelper import ApiTelegramException
    
    max_retries = 5
    retry_delay = 10  # seconds
    
    for attempt in range(max_retries):
        try:
            print(f"Starting bot (attempt {attempt + 1}/{max_retries})...")
            
            # Test the bot token first
            try:
                me = bot.get_me()
                print(f"Bot authenticated: @{me.username}")
            except Exception as e:
                print(f"Bot authentication failed: {e}")
                if attempt == max_retries - 1:
                    print("Max retries reached. Exiting.")
                    exit(1)
                time.sleep(retry_delay)
                continue
            
            # Start polling with error handling
            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=30,
                logger_level=40,  # ERROR level
                allowed_updates=None,
                restart_on_change=False,
                skip_pending=True
            )
            
            # If we reach here, polling stopped normally
            print("Bot polling stopped normally")
            break
            
        except ApiTelegramException as e:
            print(f"Telegram API error: {e}")
            if "unauthorized" in str(e).lower():
                print("Invalid bot token. Please check TELEGRAM_BOT_TOKEN environment variable.")
                exit(1)
            elif attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Exiting.")
                exit(1)
                
        except requests.exceptions.ConnectionError as e:
            print(f"Network connection error: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Exiting.")
                exit(1)
                
        except Exception as e:
            print(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Exiting.")
                exit(1)
    
    print("Bot stopped.")
