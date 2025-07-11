# Timezone Bot for Slack - Automatically converts times between timezones
import os
import re
import pytz
import json
from datetime import datetime, time
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

load_dotenv()

app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

DEFAULT_TIMEZONE = os.environ.get("DEFAULT_TIMEZONE", "America/New_York")

# Common timezone abbreviations mapping
TIMEZONE_MAPPING = {
    'EST': 'America/New_York',
    'EDT': 'America/New_York',
    'CST': 'America/Chicago',
    'CDT': 'America/Chicago',
    'MST': 'America/Denver',
    'MDT': 'America/Denver',
    'PST': 'America/Los_Angeles',
    'PDT': 'America/Los_Angeles',
    'GMT': 'GMT',
    'UTC': 'UTC',
    'BST': 'Europe/London',
    'CET': 'Europe/Paris',
    'CEST': 'Europe/Paris',
    'JST': 'Asia/Tokyo',
    'IST': 'Asia/Kolkata',
    'AEST': 'Australia/Sydney',
    'AEDT': 'Australia/Sydney',
    'SGT': 'Asia/Singapore',
    'HKT': 'Asia/Hong_Kong',
    'KST': 'Asia/Seoul',
    'WET': 'Europe/Lisbon',
    'EET': 'Europe/Athens',
    'CAT': 'Africa/Cairo',
    'WAT': 'Africa/Lagos',
    'NZST': 'Pacific/Auckland',
    'NZDT': 'Pacific/Auckland',
}

USER_PREFERENCES_FILE = 'user_preferences.json'

def load_user_preferences():
    try:
        if os.path.exists(USER_PREFERENCES_FILE):
            with open(USER_PREFERENCES_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Oops, couldn't load user settings: {e}")
    return {}

def save_user_preferences(preferences):
    try:
        with open(USER_PREFERENCES_FILE, 'w') as f:
            json.dump(preferences, f, indent=2)
    except Exception as e:
        print(f"Oops, couldn't save user settings: {e}")

USER_TIMEZONES = load_user_preferences()

class TimezoneBot:
    def __init__(self, default_tz=DEFAULT_TIMEZONE):
        self.default_tz = default_tz
        
    def extract_times_from_text(self, text):
        """Find all the times mentioned in a message"""
        # Regex patterns for different time formats
        patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm)\s*([A-Z]{3,4})',  # "4:30 PM EST"
            r'(\d{1,2}):(\d{2})\s*(am|pm)(?!\s*[A-Z]{3,4})', # "4:30 PM" (no timezone)
            r'(\d{1,2})\s*(am|pm)\s*([A-Z]{3,4})',          # "4 PM EST" 
            r'(\d{1,2})\s*(am|pm)(?!\s*[A-Z]{3,4})',        # "4 PM" (no timezone)
            r'(\d{1,2}):(\d{2})\s*([A-Z]{3,4})',            # "16:30 EST" (24-hour)
        ]
        
        found_times = []
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                found_times.append({
                    'full_match': match.group(0),
                    'groups': match.groups(),
                    'start': match.start(),
                    'end': match.end()
                })
        
        # Remove overlapping matches and sort by position
        found_times.sort(key=lambda x: x['start'])
        unique_times = []
        
        for time_match in found_times:
            overlap = False
            for existing in unique_times:
                if (time_match['start'] < existing['end'] and 
                    time_match['end'] > existing['start']):
                    overlap = True
                    break
            if not overlap:
                unique_times.append(time_match)
        
        return unique_times
    
    def parse_time_string(self, time_groups):
        """Parse time components from regex groups"""
        groups = [g for g in time_groups if g is not None]
        
        if len(groups) == 4:  # "4:30 PM EST"
            hour, minute, ampm, tz = groups
            return int(hour), int(minute), ampm.upper(), tz.upper()
            
        elif len(groups) == 3:
            if groups[2].upper() in TIMEZONE_MAPPING:  # "16:30 EST"
                hour, minute, tz = groups
                return int(hour), int(minute), None, tz.upper()
            elif groups[2].upper() in ['AM', 'PM']:  # "4:30 PM"
                hour, minute, ampm = groups
                return int(hour), int(minute), ampm.upper(), None
            else:  # "4 PM EST"
                hour, ampm, tz = groups
                return int(hour), 0, ampm.upper(), tz.upper()
                
        elif len(groups) == 2:  # "4 PM" or "16:30"
            if groups[1].upper() in ['AM', 'PM']:
                hour, ampm = groups
                return int(hour), 0, ampm.upper(), None
            else:
                hour, minute = groups
                return int(hour), int(minute), None, None
        
        return None, None, None, None
    
    def convert_to_24hour(self, hour, minute, ampm):
        """Convert 12-hour format to 24-hour format"""
        if ampm == 'PM' and hour != 12:
            hour += 12
        elif ampm == 'AM' and hour == 12:
            hour = 0  # 12 AM becomes midnight
        return hour, minute
    
    def convert_timezone(self, hour, minute, from_tz, to_tz):
        """Convert a time from one timezone to another"""
        try:
            from_timezone = pytz.timezone(from_tz)
            to_timezone = pytz.timezone(to_tz)
            
            today = datetime.now().date()
            dt = datetime.combine(today, time(hour, minute))
            
            dt_localized = from_timezone.localize(dt)
            dt_converted = dt_localized.astimezone(to_timezone)
            
            return dt_converted
        except Exception as e:
            print(f"Oops, couldn't convert timezone: {e}")
            return None
    
    def format_time_response(self, original_time, converted_time, target_tz):
        if converted_time:
            formatted_time = converted_time.strftime("%I:%M %p").lstrip('0')
            tz_name = converted_time.strftime("%Z")
            
            if not tz_name:
                tz_name = target_tz.split('/')[-1]
            
            return f"`{original_time}` → **{formatted_time} {tz_name}**"
        return None
    
    def process_message(self, text, target_timezone=None):
        """Main function - find times in a message and convert them"""
        if not target_timezone:
            target_timezone = self.default_tz
            
        found_times = self.extract_times_from_text(text)
        conversions = []
        
        for time_match in found_times:
            groups = time_match['groups']
            original_text = time_match['full_match']
            
            hour, minute, ampm, source_tz = self.parse_time_string(groups)
            
            if hour is None:
                continue
            
            # Convert 12-hour to 24-hour if needed
            if ampm:
                hour, minute = self.convert_to_24hour(hour, minute, ampm)
            
            # Skip if no timezone was mentioned
            if source_tz and source_tz in TIMEZONE_MAPPING:
                source_timezone = TIMEZONE_MAPPING[source_tz]
            else:
                continue
            
            # Skip if already in target timezone
            if source_timezone == target_timezone:
                continue
            
            converted_time = self.convert_timezone(hour, minute, source_timezone, target_timezone)
            
            if converted_time:
                response = self.format_time_response(original_text, converted_time, target_timezone)
                if response:
                    conversions.append(response)
        
        return conversions

timezone_bot = TimezoneBot()

@app.event("message")
def handle_message(event, say):
    # Ignore bot messages
    if event.get("subtype") == "bot_message" or event.get("bot_id"):
        return
    
    text = event.get("text", "")
    user_id = event.get("user")
    
    user_timezone = USER_TIMEZONES.get(user_id, DEFAULT_TIMEZONE)
    conversions = timezone_bot.process_message(text, user_timezone)
    
    if conversions:
        response = "⏰ **Time Conversion:**\n" + "\n".join(conversions)
        say(response)

@app.event("app_mention")
def handle_app_mention(event, say):
    text = event.get("text", "")
    user_id = event.get("user")
    
    user_timezone = USER_TIMEZONES.get(user_id, DEFAULT_TIMEZONE)
    conversions = timezone_bot.process_message(text, user_timezone)
    
    if conversions:
        response = "⏰ **Time Conversion:**\n" + "\n".join(conversions)
        say(response)
    else:
        say("I couldn't find any times to convert in your message. Try mentioning a time like '4 PM EST' or '14:30 PST'!")

@app.command("/settimezone")
def set_timezone(ack, respond, command):
    ack()
    
    timezone_name = command['text'].strip()
    user_id = command['user_id']
    
    if not timezone_name:
        respond("Please provide a timezone. Example: `/settimezone America/New_York`")
        return
    
    try:
        pytz.timezone(timezone_name)  # Validate timezone
        USER_TIMEZONES[user_id] = timezone_name
        save_user_preferences(USER_TIMEZONES)
        respond(f"Your timezone has been set to `{timezone_name}`")
    except:
        respond("Invalid timezone. Please use a valid timezone like `America/New_York`, `Europe/London`, or `Asia/Tokyo`.\n\nYou can find a list of valid timezones here: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones")

@app.command("/convert")
def convert_time(ack, respond, command):
    ack()
    
    text = command['text']
    user_id = command['user_id']
    
    if not text:
        respond("Please provide a time to convert. Example: `/convert 4 PM EST`")
        return
    
    user_timezone = USER_TIMEZONES.get(user_id, DEFAULT_TIMEZONE)
    conversions = timezone_bot.process_message(text, user_timezone)
    
    if conversions:
        response = "⏰ **Time Conversion:**\n" + "\n".join(conversions)
        respond(response)
    else:
        respond("I couldn't find any times to convert. Try something like `4 PM EST`, `14:30 PST`, or `9 AM GMT`")

@app.command("/mytimezone")
def show_timezone(ack, respond, command):
    ack()
    
    user_id = command['user_id']
    user_timezone = USER_TIMEZONES.get(user_id, DEFAULT_TIMEZONE)
    
    tz = pytz.timezone(user_timezone)
    current_time = datetime.now(tz)
    formatted_time = current_time.strftime("%I:%M %p %Z")
    
    respond(f"Your timezone is set to: `{user_timezone}`\nCurrent time: **{formatted_time}**")

@app.event("app_home_opened")
def handle_app_home_opened(event, say):
    user_id = event['user']
    user_timezone = USER_TIMEZONES.get(user_id, DEFAULT_TIMEZONE)
    
    welcome_message = f"""
👋 Hello! I'm your timezone conversion bot.

**What I do:**
• I automatically detect times in messages and convert them to your timezone
• I support formats like "4 PM EST", "14:30 PST", "9 AM GMT"
• I can handle common timezone abbreviations

**Your Settings:**
Current timezone: `{user_timezone}`

**Commands:**
• `/settimezone America/New_York` - Set your timezone
• `/convert 4 PM EST` - Manually convert a time
• `/mytimezone` - Check your current timezone

**Example:**
If someone writes "Meeting at 4 PM EST", I'll automatically convert it to your timezone!

Try mentioning a time in any channel where I'm added, or use the commands above to get started.
"""
    
    say(welcome_message)

@app.error
def global_error_handler(error, body, logger):
    logger.exception(f"Something went wrong: {error}")
    logger.info(f"Request details: {body}")

if __name__ == "__main__":
    print("Starting Timezone Bot...")
    print(f"Default timezone: {DEFAULT_TIMEZONE}")
    print("Connecting to Slack...")
    
    try:
        handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
        handler.start()
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Error starting bot: {e}")
        print("Please check your environment variables and try again.")