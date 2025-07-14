# Multi-Platform Timezone Bot

A timezone conversion bot supporting Discord, Slack, and Telegram with consistent commands and behavior across platforms.

## Commands (Available on all platforms)

- `/timezone <timezone>` - Set your personal timezone
- `/time <message> [timezone]` - Convert times to your timezone (or specified timezone)  
- `/mytimezone` - Show your current timezone setting and current time
- `/help` - Show help information and available commands

## Discord Features

### Emoji Reactions
React to any message containing times with time-related emojis to get instant timezone conversions:
- 🕐 (clock face) ⏰ (alarm clock) ⏳ (hourglass) ⏲️ (timer)

The bot will DM you the converted times in your timezone.

## Supported Formats

**Times**: `3:00 PM`, `15:30`, `3 PM EST`, `at 3pm`  
**Timezones**: `EST`, `PST`, `America/New_York`, `UTC-5`, `+0530`


## Supported Time Formats

The bot can detect and parse various time formats:

- **12-hour format**: `3:00 PM`, `3 PM`, `3:30 AM`
- **24-hour format**: `15:00`, `09:30`, `23:45`
- **With timezones**: `3 PM EST`, `15:00 UTC`, `2:30 AM PST`
- **With context words**: `at 3pm`, `around 15:30`, `before 2 PM`

## Supported Timezone Formats

- **Abbreviations**: EST, PST, GMT, UTC, CET, JST, IST, AEST
- **IANA zones**: America/New_York, Europe/London, Asia/Tokyo
- **UTC offsets**: UTC-5, UTC+5:30, +0530, -0800

## Usage Examples

### Setup
1. Set your timezone: `/timezone EST`
2. Convert times: `/time "Meeting at 3 PM GMT"`
3. Check your settings: `/mytimezone`

### Discord Emoji Reactions
1. Someone posts: "Let's meet at 3 PM EST tomorrow"
2. React with ⏰ emoji  
3. Get a DM with converted times in your timezone

### All Platforms
All bots provide identical functionality with automatic time detection and consistent response formatting.

## License

MIT License - see LICENSE file for details.
