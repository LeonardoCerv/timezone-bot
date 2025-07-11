"""
Timezone Bot for Telegram

A bot that automatically detects times in messages and converts them to users' preferred timezones.
Supports commands for setting timezone preferences and manual time conversion.

Features:
- Automatic time detection and conversion
- User timezone preferences
- Support for timezone abbreviations (EST, PST, etc.)
- Manual conversion commands

Commands:
/start - Welcome message and setup
/timezone <timezone> - Set your preferred timezone
/convert <time> - Convert a time to your timezone
/mytimezone - Show your current timezone setting
/help - Show help message
"""

import os
import re
import json
import pytz
import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
import telebot
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
DEFAULT_TIMEZONE = os.getenv('DEFAULT_TIMEZONE', 'America/New_York')
USER_PREFERENCES_FILE = 'user_preferences.json'

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

class UserPreferences:
    """Handle user preference storage and retrieval"""
    
    def __init__(self, filename: str = USER_PREFERENCES_FILE):
        self.filename = filename
        self.preferences = self._load_preferences()
    
    def _load_preferences(self) -> Dict:
        """Load user preferences from JSON file"""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading user preferences: {e}")
        return {}
    
    def _save_preferences(self) -> None:
        """Save user preferences to JSON file"""
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.preferences, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving user preferences: {e}")
    
    def set_timezone(self, user_id: int, timezone: str) -> bool:
        """Set timezone for a user"""
        try:
            # Validate timezone
            pytz.timezone(timezone)
            self.preferences[str(user_id)] = {
                'timezone': timezone,
                'updated_at': datetime.now().isoformat()
            }
            self._save_preferences()
            return True
        except Exception as e:
            logger.error(f"Error setting timezone for user {user_id}: {e}")
            return False
    
    def get_timezone(self, user_id: int) -> str:
        """Get timezone for a user, return default if not set"""
        user_prefs = self.preferences.get(str(user_id))
        if user_prefs:
            return user_prefs.get('timezone', DEFAULT_TIMEZONE)
        return DEFAULT_TIMEZONE

class TimezoneBot:
    """Main timezone conversion bot logic"""
    
    def __init__(self):
        self.user_prefs = UserPreferences()
    
    def normalize_timezone(self, timezone_input: str) -> Optional[str]:
        """Convert timezone input to a valid pytz timezone"""
        if not timezone_input:
            return None
        
        # Check abbreviations first
        timezone_upper = timezone_input.upper()
        if timezone_upper in TIMEZONE_MAPPING:
            return TIMEZONE_MAPPING[timezone_upper]
        
        # Check if it's a valid pytz timezone
        try:
            pytz.timezone(timezone_input)
            return timezone_input
        except pytz.exceptions.UnknownTimeZoneError:
            pass
        
        # Handle UTC offset formats like UTC-5, UTC+3
        offset_match = re.match(r'^(UTC)?([+-]?\d{1,2}):?(\d{2})?$', timezone_input, re.IGNORECASE)
        if offset_match:
            sign = '+' if offset_match.group(2).startswith('+') else '-'
            hours = abs(int(offset_match.group(2)))
            minutes = int(offset_match.group(3)) if offset_match.group(3) else 0
            
            # Validate reasonable offset ranges
            if hours <= 14 and minutes <= 59:
                # Etc/GMT offsets are inverted (GMT+5 = UTC-5)
                return f"Etc/GMT{'-' if sign == '+' else '+'}{hours}"
        
        return None
    
    def extract_times_from_text(self, text: str) -> List[Dict]:
        """Extract time mentions from text"""
        # Regex patterns for different time formats
        patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm)\s*([A-Z]{3,4})',  # "4:30 PM EST"
            r'(\d{1,2})\s*(am|pm)\s*([A-Z]{3,4})',          # "4 PM EST" 
            r'(\d{1,2}):(\d{2})\s*([A-Z]{3,4})',            # "16:30 EST" (24-hour)
            r'(\d{1,2}):(\d{2})\s*(am|pm)(?!\s*[A-Z]{3,4})', # "4:30 PM" (no timezone)
            r'(\d{1,2})\s*(am|pm)(?!\s*[A-Z]{3,4})',        # "4 PM" (no timezone)
            r'(\d{1,2}):(\d{2})(?!\s*[a-zA-Z])',            # "16:30" (24-hour, no timezone)
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
    
    def parse_time_string(self, time_groups: Tuple) -> Tuple[Optional[int], Optional[int], Optional[str], Optional[str]]:
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
    
    def convert_to_24hour(self, hour: int, minute: int, ampm: Optional[str]) -> Tuple[int, int]:
        """Convert 12-hour format to 24-hour format"""
        if ampm == 'PM' and hour != 12:
            hour += 12
        elif ampm == 'AM' and hour == 12:
            hour = 0  # 12 AM becomes midnight
        return hour, minute
    
    def convert_timezone(self, hour: int, minute: int, from_tz: str, to_tz: str) -> Optional[datetime]:
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
            logger.error(f"Error converting timezone: {e}")
            return None
    
    def format_time_response(self, original_time: str, converted_time: datetime, target_tz: str) -> str:
        """Format the conversion response"""
        if converted_time:
            formatted_time = converted_time.strftime("%I:%M %p").lstrip('0')
            tz_name = converted_time.strftime("%Z")
            
            if not tz_name:
                tz_name = target_tz.split('/')[-1]
            
            # Check if it's a different day
            today = datetime.now().date()
            if converted_time.date() != today:
                date_info = f" ({converted_time.strftime('%a, %b %d')})"
            else:
                date_info = ""
            
            return f"`{original_time}` → **{formatted_time} {tz_name}**{date_info}"
        return None
    
    def process_message(self, text: str, user_id: int, target_timezone: Optional[str] = None) -> List[str]:
        """Main function - find times in a message and convert them"""
        if not target_timezone:
            target_timezone = self.user_prefs.get_timezone(user_id)
        
        # Normalize target timezone
        normalized_target = self.normalize_timezone(target_timezone)
        if not normalized_target:
            return []
        
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
            
            # Skip if no timezone was mentioned (for automatic detection)
            # For convert command, we'll handle this differently
            if not source_tz or source_tz not in TIMEZONE_MAPPING:
                continue
            
            source_timezone = TIMEZONE_MAPPING[source_tz]
            
            # Skip if already in target timezone
            if source_timezone == normalized_target:
                continue
            
            converted_time = self.convert_timezone(hour, minute, source_timezone, normalized_target)
            
            if converted_time:
                response = self.format_time_response(original_text, converted_time, normalized_target)
                if response:
                    conversions.append(response)
        
        return conversions

# Initialize the bot
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)
timezone_bot = TimezoneBot()

# Command handlers
@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Handle /start command"""
    user_tz = timezone_bot.user_prefs.get_timezone(message.from_user.id)
    
    welcome_message = f"""🌍 *Welcome to Timezone Bot!*

I help you convert times between different timezones automatically.

*What I can do:*
• Automatically detect times in messages and convert them
• Support formats like "4 PM EST", "14:30 PST", "9 AM GMT"
• Remember your preferred timezone
• Manual time conversion

*Your current timezone:* `{user_tz}`

*Commands:*
/timezone `EST` - Set your timezone
/convert `4 PM EST` - Convert a time
/mytimezone - Check your timezone
/help - Show this help

*Example:*
If someone writes "Meeting at 4 PM EST", I'll convert it to your timezone!

Try sending me a message with a time, or use the commands above."""

    bot.reply_to(message, welcome_message, parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def send_help(message):
    """Handle /help command"""
    help_text = """🕐 *Timezone Bot Help*

*Commands:*
/start - Welcome message and setup
/timezone `<timezone>` - Set your preferred timezone
/convert `<time>` - Convert a time to your timezone
/mytimezone - Show your current timezone
/help - Show this help

*Supported Time Formats:*
• `4 PM EST` - 12-hour with timezone
• `4:30 PM PST` - 12-hour with minutes
• `16:30 GMT` - 24-hour format
• `14:00 UTC` - 24-hour format

*Supported Timezones:*
• Abbreviations: EST, PST, GMT, UTC, etc.
• Full names: America/New_York, Europe/London
• UTC offsets: UTC-5, UTC+3

*Auto-Detection:*
I automatically detect times in your messages and convert them to your timezone. Just mention a time with a timezone and I'll help!

*Examples:*
• "Meeting at 3 PM EST tomorrow"
• "Call scheduled for 14:30 GMT"
• "Deadline is 5 PM PST on Friday"
"""
    
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['timezone'])
def handle_timezone_command(message):
    """Handle /timezone command"""
    user_id = message.from_user.id
    
    # Parse command arguments
    command_parts = message.text.split()
    
    if len(command_parts) == 1:  # Just /timezone
        current_tz = timezone_bot.user_prefs.get_timezone(user_id)
        bot.reply_to(message,
            f"Your current timezone is: `{current_tz}`\n\n"
            "To set a new timezone, use: `/timezone EST` or `/timezone America/New_York`",
            parse_mode="Markdown"
        )
        return
    
    timezone_input = ' '.join(command_parts[1:])
    normalized_tz = timezone_bot.normalize_timezone(timezone_input)
    
    if not normalized_tz:
        bot.reply_to(message,
            "❌ Invalid timezone. Please use formats like:\n"
            "• `EST`, `PST`, `GMT`, `UTC`\n"
            "• `America/New_York`, `Europe/London`\n"
            "• `UTC-5`, `UTC+3`\n\n"
            "Find more timezones at: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones",
            parse_mode="Markdown"
        )
        return
    
    success = timezone_bot.user_prefs.set_timezone(user_id, normalized_tz)
    
    if success:
        # Show current time in the new timezone
        tz = pytz.timezone(normalized_tz)
        current_time = datetime.now(tz)
        formatted_time = current_time.strftime("%I:%M %p %Z").lstrip('0')
        
        bot.reply_to(message,
            f"✅ Timezone set to `{normalized_tz}`\n"
            f"Current time: **{formatted_time}**\n\n"
            "Now I'll automatically convert times to your timezone!",
            parse_mode="Markdown"
        )
    else:
        bot.reply_to(message,
            "❌ Failed to save timezone. Please try again.",
            parse_mode="Markdown"
        )

@bot.message_handler(commands=['convert'])
def handle_convert_command(message):
    """Handle /convert command"""
    user_id = message.from_user.id
    
    # Parse command arguments
    command_parts = message.text.split(maxsplit=1)
    
    if len(command_parts) == 1:  # Just /convert
        bot.reply_to(message,
            "Please provide a time to convert. Examples:\n"
            "• `/convert 4 PM EST`\n"
            "• `/convert 14:30 PST`\n"
            "• `/convert 9 AM GMT`\n"
            "• `/convert 4 PM` (assumes UTC)",
            parse_mode="Markdown"
        )
        return
    
    time_text = command_parts[1]
    
    # First try normal processing
    conversions = timezone_bot.process_message(time_text, user_id)
    
    # If no conversions found, try with UTC as default source timezone
    if not conversions:
        # Check if we can extract time without timezone
        found_times = timezone_bot.extract_times_from_text(time_text)
        
        for time_match in found_times:
            groups = time_match['groups']
            original_text = time_match['full_match']
            
            hour, minute, ampm, source_tz = timezone_bot.parse_time_string(groups)
            
            if hour is None:
                continue
            
            # Convert 12-hour to 24-hour if needed
            if ampm:
                hour, minute = timezone_bot.convert_to_24hour(hour, minute, ampm)
            
            # If no timezone provided, assume UTC
            if not source_tz:
                source_timezone = 'UTC'
                user_tz = timezone_bot.user_prefs.get_timezone(user_id)
                normalized_target = timezone_bot.normalize_timezone(user_tz)
                
                if normalized_target and source_timezone != normalized_target:
                    converted_time = timezone_bot.convert_timezone(hour, minute, source_timezone, normalized_target)
                    
                    if converted_time:
                        response = timezone_bot.format_time_response(f"{original_text} UTC", converted_time, normalized_target)
                        if response:
                            conversions.append(response)
    
    if conversions:
        user_tz = timezone_bot.user_prefs.get_timezone(user_id)
        response = f"🕐 *Time Conversion to {user_tz}:*\n\n" + "\n".join(conversions)
        bot.reply_to(message, response, parse_mode="Markdown")
    else:
        bot.reply_to(message,
            "❌ I couldn't find any times to convert. Make sure to include a valid time!\n\n"
            "Examples: `4 PM EST`, `14:30 PST`, `9 AM GMT`, or `4 PM` (assumes UTC)",
            parse_mode="Markdown"
        )

@bot.message_handler(commands=['mytimezone'])
def handle_mytimezone_command(message):
    """Handle /mytimezone command"""
    user_id = message.from_user.id
    user_timezone = timezone_bot.user_prefs.get_timezone(user_id)
    
    try:
        tz = pytz.timezone(user_timezone)
        current_time = datetime.now(tz)
        formatted_time = current_time.strftime("%I:%M %p %Z").lstrip('0')
        date_str = current_time.strftime("%A, %B %d, %Y")
        
        bot.reply_to(message,
            f"🌍 *Your Timezone Settings*\n\n"
            f"Timezone: `{user_timezone}`\n"
            f"Current time: **{formatted_time}**\n"
            f"Date: {date_str}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Error showing timezone for user {user_id}: {e}")
        bot.reply_to(message,
            f"Your timezone is set to: `{user_timezone}`\n\n"
            "Use `/timezone` to change it.",
            parse_mode="Markdown"
        )

# Handle regular messages for automatic time detection
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Handle regular messages for automatic time detection"""
    if not message.text:
        return
    
    user_id = message.from_user.id
    text = message.text
    
    # Skip if message starts with a command
    if text.startswith('/'):
        return
    
    conversions = timezone_bot.process_message(text, user_id)
    
    if conversions:
        user_tz = timezone_bot.user_prefs.get_timezone(user_id)
        response = f"🕐 *Converted to your timezone ({user_tz}):*\n\n" + "\n".join(conversions)
        bot.reply_to(message, response, parse_mode="Markdown")

def main():
    """Start the bot"""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        return
    
    print("🤖 Starting Timezone Bot for Telegram...")
    print(f"📍 Default timezone: {DEFAULT_TIMEZONE}")
    print("✅ Bot is ready! Starting polling...")
    print("\nAvailable commands:")
    print("  /start - Welcome message")
    print("  /timezone EST - Set your timezone")
    print("  /convert '4 PM EST' - Convert time")
    print("  /mytimezone - Show your timezone")
    print("  /help - Show help")
    print("\nAutomatic detection:")
    print("  Send any message with times like '3 PM EST' and I'll convert them!")
    
    # Start the bot
    bot.infinity_polling()

if __name__ == '__main__':
    main()
