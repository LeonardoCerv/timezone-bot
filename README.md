# Discord Timezone Bot

A Discord bot that converts times between timezones using slash commands and emoji reactions.

## Features

### Slash Commands
- `/timezone <timezone>` - Set your personal timezone
- `/time <message> [timezone]` - Convert times in a message to your timezone (or specified timezone)

### Emoji Reactions 🆕
React to any message containing times with time-related emojis to get instant timezone conversions:
- 🕐 (clock face)
- ⏰ (alarm clock) 
- ⏳ (hourglass)
- ⏲️ (timer)

The bot will DM you the converted times in your timezone. Set your timezone first with `/timezone`!

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

### Personal Timezone Setup
1. Set your timezone: `/timezone EST`
2. Use `/time` command: `/time "Meeting at 3 PM GMT"`
3. **OR** React to any message containing times with 🕐, ⏰, ⏳, or ⏲️ for instant conversion

### Quick Reaction Conversion
1. Someone posts: "Let's meet at 3 PM EST tomorrow"
2. React with ⏰ emoji
3. Get a DM with: "⏰ **Times converted to your timezone (PST):** **3 PM EST** → **12:00 PM PST**"

## License

MIT License - see LICENSE file for details.
