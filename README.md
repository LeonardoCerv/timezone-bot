# Discord Timezone Bot

A simple, clean Discord bot that converts times between timezones. Set your timezone once, then easily convert any times you see in messages.

## Commands

**`/timezone <timezone>`** - Set your personal timezone  
**`/time <message> [timezone]`** - Convert times in a message

## Examples

```
/timezone EST
/time "Meeting at 3 PM PST"
→ Meeting at 3 PM PST → 6:00 PM EST

/time "Call tomorrow at 2 PM GMT" "JST" 
→ Call tomorrow at 2 PM GMT → 11:00 PM JST
```

## Supported Formats

**Times**: `3:00 PM`, `15:30`, `3 PM EST`, `at 3pm`  
**Timezones**: `EST`, `PST`, `America/New_York`, `UTC-5`, `+0530`

## Setup

1. `npm install`
2. Create `.env` with your Discord credentials
3. `npm run register` 
4. `npm start`

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

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```

2. Set up environment variables in `.env`:
   ```
   APP_ID=your_discord_app_id
   PUBLIC_KEY=your_discord_public_key
   BOT_TOKEN=your_discord_bot_token
   ```

3. Register commands with Discord:
   ```bash
   npm run register
   ```

4. Start the bot:
   ```bash
   npm start
   ```

## Usage Examples

### Personal Timezone Setup
1. Set your timezone: `/timezone EST`
2. Now you can use `/time` or right-click messages to get times in your timezone

### Message Reply Workflow
1. Someone posts: "Team meeting tomorrow at 3 PM PST"
2. Reply to their message with: `/time`
3. Get ephemeral response: "🕐 **3 PM PST** → **6:00 PM EST**"

### Universal Translation
1. Someone posts: "Deadline is 5 PM GMT"
2. Reply with: `/translate JST`
3. Get ephemeral response: "🌍 **5 PM GMT** → **2:00 AM JST** (Saturday, January 11th)"

### Context Menu
1. Right-click any message containing times
2. Select "Convert to my timezone"
3. Get instant ephemeral conversion to your personal timezone

## Privacy

- All timezone conversions are sent as ephemeral messages (only visible to you)
- User timezone preferences are stored locally in `timezones.json`
- No message content is logged or stored permanently

## Dependencies

- `discord-interactions`: Discord API interactions
- `express`: Web server for webhook handling
- `moment-timezone`: Timezone conversion and parsing
- `dotenv`: Environment variable management

## License

MIT License - see LICENSE file for details.
