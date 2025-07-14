# Multi-Platform Timezone Bot

A comprehensive timezone conversion bot supporting Discord, Slack, and Telegram platforms with consistent commands and behavior across all environments.

## Installation

Deploy the bot to your preferred platform:

### Discord
[![Add to Discord](https://img.shields.io/badge/Add%20to-Discord-7289DA?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/oauth2/authorize?client_id=1392192666053251143&permissions=8&integration_type=0&scope=bot+applications.commands)

### Slack  
[![Add to Slack](https://img.shields.io/badge/Add%20to-Slack-4A154B?style=for-the-badge&logo=slack&logoColor=white)](https://slack.com/oauth/v2/authorize?client_id=9180592732466.9175325235619&scope=channels:read,chat:write,app_mentions:read,channels:history,groups:history,im:history,commands&user_scope=)

### Telegram
[![Start Bot](https://img.shields.io/badge/Start-Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/TimeZone123Bot)

## Commands

Available across all supported platforms:

- `/timezone <timezone>` - Set your personal timezone
- `/time <message> [timezone]` - Convert times to your timezone or specified timezone
- `/mytimezone` - Display your current timezone setting and local time
- `/help` - Show help information and available commands

## Platform-Specific Features

### Discord
**Emoji Reactions**: React to messages containing times with time-related emojis for instant timezone conversions:
- Clock face, alarm clock, hourglass, or timer emojis
- Converted times will be sent via direct message

## Supported Formats

**Time Formats**:
- 12-hour format: `3:00 PM`, `3 PM`, `3:30 AM`
- 24-hour format: `15:00`, `09:30`, `23:45`
- With timezone: `3 PM EST`, `15:00 UTC`, `2:30 AM PST`
- With context: `at 3pm`, `around 15:30`, `before 2 PM`

**Timezone Formats**:
- Abbreviations: EST, PST, GMT, UTC, CET, JST, IST, AEST
- IANA zones: America/New_York, Europe/London, Asia/Tokyo
- UTC offsets: UTC-5, UTC+5:30, +0530, -0800

## Usage Examples

### Initial Setup
1. Set your timezone: `/timezone EST`
2. Convert times in messages: `/time "Meeting at 3 PM GMT"`
3. Check your current settings: `/mytimezone`

### Discord Emoji Reactions
1. User posts: "Let's meet at 3 PM EST tomorrow"
2. React with a time-related emoji
3. Receive converted times via direct message

### Cross-Platform Consistency
All bot implementations provide identical functionality with automatic time detection and consistent response formatting across Discord, Slack, and Telegram.

## Development Setup

### Discord Bot
```bash
cd Discord
npm install
# Create .env file with DISCORD_TOKEN and CLIENT_ID
npm run register  # Register slash commands
npm start
```

### Slack Bot  
```bash
cd Slack
pip install -r requirements.txt
# Create .env file with SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET
python app.py
```

### Telegram Bot
```bash
cd Telegram  
pip install -r requirements.txt
# Create .env file with TELEGRAM_BOT_TOKEN
python app.py
```

## Project Structure

```
query-bot/
├── Discord/          # Discord bot implementation (Node.js)
│   ├── bot.js
│   ├── register.js
│   └── package.json
├── Slack/           # Slack bot implementation (Python)
│   ├── app.py
│   ├── oauth_server.py
│   └── requirements.txt
├── Telegram/        # Telegram bot implementation (Python)
│   ├── app.py
│   └── requirements.txt
└── shared/          # Shared configuration and resources
    ├── response_messages.json
    ├── timezones.json
    └── user_preferences.json
```

## License

MIT License - see LICENSE file for details.
