
> 📖 🇪🇸 También disponible en español: [README.es.md](README.es.md)

# Timezone Bot

![Typescript](https://img.shields.io/badge/Typescript-3178C6?logo=Typescript&logoColor=white)
![Python](https://img.shields.io/badge/Python-yellow?logo=Python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-307387?logo=flask&logoColor=white)
![Node.js](https://img.shields.io/badge/NodeJS-339933?logo=nodedotjs&logoColor=white)
![Express](https://img.shields.io/badge/Express-000000?logo=express&logoColor=white)
![Field](https://img.shields.io/badge/Field-Bots-white)
![License](https://img.shields.io/badge/License-MIT-brown)

A bot to help you convert different timezones inside messages in **Discord**/**Slack**/**Telegram**.This bot doesnt interfere with other messages in the channel so its perfect for big servers.

## Available Platforms
| Discord | Slack | Telegram |
|---------|-------|----------|
| [![Add to Discord](https://img.shields.io/badge/Add%20to-Discord-7289DA?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/oauth2/authorize?client_id=1392192666053251143&permissions=8&integration_type=0&scope=bot+applications.commands) <img src="Discord.png" alt="Discord Bot" width="200" height="150"> | [![Add to Slack](https://img.shields.io/badge/Add%20to-Slack-4A154B?style=for-the-badge&logo=slack&logoColor=white)](https://slack.com/oauth/v2/authorize?client_id=9180592732466.9175325235619&scope=channels:read,chat:write,app_mentions:read,channels:history,groups:history,im:history,commands&user_scope=) <img src="Slack.png" alt="Slack Bot" width="200" height="150"> | [![Start Telegram](https://img.shields.io/badge/Start-Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/TimeZone123Bot) <img src="Telegram.png" alt="Telegram Bot" width="200" height="150"> |

## What it does

Picture this: you're coordinating a meeting with teammates across three continents. Someone says "let's meet at 3pm EST" and suddenly everyone's doing mental math. Your London colleague is calculating GMT, your Tokyo teammate is figuring out JST, and you're just trying to remember if you're in PST or PDT.

This bot solves that problem. It lives quietly in your Discord servers, Slack workspaces, and Telegram chats, waiting for you to use it, and when you do, it shows ephemeral messages, it makes sure to not interrupt the conversacion or cluterring the channel.

**How it works:**
- Someone types `/time 3pm EST` or just mentions a time in conversation
- On Discord, anyone can react with ⏰ to any message containing time
- The bot privately responds with conversions to your timezone and other popular zones
- It remembers your timezone preference across all platforms
- Supports 200+ timezone aliases (EST, PST, GMT, JST, etc.)

**Example conversation:**
```
Alice: "Daily standup is at 9am PST tomorrow"
[Someone reacts with ⏰]
Bot (privately): 🕒 9:00 AM PST
                🌍 Your timezone: 12:00 PM EST  
                🌏 UTC: 5:00 PM
                🌍 London: 5:00 PM GMT
```

## Running it yourself

Want to run your own version? Here's how each platform works:

### Requirements

Before diving into platform-specific setup, you'll need different infrastructure depending on which bots you want to run:

**For Discord & Slack bots:**
- A server with a public IP address or domain name
- HTTPS support (required for webhooks)
- Port access for incoming requests (Discord uses webhooks, Slack uses Socket Mode but OAuth requires endpoints)
- Consider services like Railway, Heroku, DigitalOcean, or AWS for hosting

**For Telegram bot:**
- No server required! Telegram uses polling, so it can run from your local machine
- Just needs an internet connection to poll for updates

**General requirements:**
- Node.js 16+ (for Discord bot)
- Python 3.8+ (for Slack and Telegram bots)
- Bot tokens and API credentials from each platform:
  - **Discord**: [Discord Developer Portal](https://discord.com/developers/applications)
  - **Slack**: [Slack API Dashboard](https://api.slack.com/apps)
  - **Telegram**: [@BotFather](https://t.me/BotFather) on Telegram

### Discord Bot Setup
```bash
cd Discord/
npm install                 # Installs express, discord-interactions, ws, moment-timezone
cp .env.example .env       # Copy environment template and fill with your tokens
npm run register           # Registers slash commands with Discord API
npm run dev               # Starts Express server on port 8943
```
> 💡 **Setup tip**: Copy `.env.example` to `.env` and fill in your Discord bot credentials from the [Discord Developer Portal](https://discord.com/developers/applications)

### Slack Bot Setup
```bash
cd Slack/
pip install -r requirements.txt  # Installs slack-bolt, flask, pytz
cp .env.example .env             # Copy environment template and fill with your tokens
python oauth_server.py           # Start OAuth server (port 8944)
python app.py                    # Start main bot server (port 8945)
```
> 💡 **Setup tip**: Copy `.env.example` to `.env` and fill in your Slack app credentials from the [Slack API Dashboard](https://api.slack.com/apps)

### Telegram Bot Setup  
```bash
cd Telegram/
pip install -r requirements.txt  # Installs pyTelegramBotAPI, pytz
cp .env.example .env             # Copy environment template and fill with your token
python app.py                    # Start bot with long polling
python web_server.py             # Start web server (port 8946)
```
> 💡 **Setup tip**: Copy `.env.example` to `.env` and fill in your bot token from [@BotFather](https://t.me/BotFather) on Telegram

## Technical Architecture

Unified timezone conversion across three platforms using shared data layer.

### Timezone pipeline

1. **Text Parsing**: Regex detects time expressions (`3pm`, `15:00`, `3:30 PM EST`)
2. **Timezone Resolution**: Maps aliases to IANA identifiers (`EST` → `America/New_York`)
3. **Conversion**: `moment-timezone` (Node.js) or `pytz` (Python)

#### **Discord** (`Discord/`): Express server + WebSocket for slash commands and ⏰ reactions  
```bash
├── bot.js           # Main bot logic, Express server, WebSocket handling
├── register.js      # One-time slash command registration
├── package.json     # Dependencies: express, discord-interactions, ws
└── .env.example     # Discord bot token, app credentials'
```

#### **Slack** (`Slack/`): Dual-process Socket Mode + Flask OAuth server  
```bash
├── app.py           # Main bot using Slack Bolt SDK
├── oauth_server.py  # Flask OAuth server for workspace installation
├── requirements.txt # Dependencies: slack-bolt, flask, pytz
└── .env.example     # Slack bot/app tokens, signing secret
```
#### **Telegram** (`Telegram/`): Single-process long polling
```bash
├── app.py           # Complete bot implementation with polling
├── requirements.txt # Dependencies: pyTelegramBotAPI, pytz  
└── .env.example     # Telegram bot token only
```

#### Shared Data (`shared/`)

```json
// timezones.json - 200+ timezone aliases
{
  "aliases": { "EST": "America/New_York" },
  "popular": ["UTC", "America/New_York", "Europe/London"]
}

// user_preferences.json - Cross-platform user timezones
{
  "discord": {"user_id": "timezone"},
  "slack": {"user_id": "timezone"},
  "telegram": {"user_id": "timezone"}
}
```

**Why JSON files**: No database dependencies for self-hosting

## Contributing

Want to help make timezone coordination easier for everyone?

1. **Fork the repo** - Start with your own copy
2. **Pick a platform** - Each has its own development environment
3. **Make your changes** - Follow existing patterns and test locally
4. **Test across platforms** - Ensure shared data changes work everywhere
5. **Submit a pull request** - We'll review and merge

The beauty of this architecture is that you can contribute to one platform without needing to understand the others. The shared data files ensure consistency across all implementations.

## License

MIT License - do whatever you want with it.