
> 📖 🇪🇸 También disponible en español: [README.es.md](README.es.md)

# Timezone Bot

![Typescript](https://img.shields.io/badge/Typescript-3178C6?logo=Typescript&logoColor=white)
![Python](https://img.shields.io/badge/Python-yellow?logo=Python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-307387?logo=flask&logoColor=white)
![Node.js](https://img.shields.io/badge/NodeJS-339933?logo=nodedotjs&logoColor=white)
![Express](https://img.shields.io/badge/Express-000000?logo=express&logoColor=white)
![Platform](https://img.shields.io/badge/Discord%20API-7289DA?logo=discord&logoColor=white)
![Platform](https://img.shields.io/badge/Slack%20API-4A154B?logo=slack&logoColor=white)
![Platform](https://img.shields.io/badge/Telegram%20API-26A5E4?logo=telegram&logoColor=white)
![Field](https://img.shields.io/badge/Field-Bot%20Development-white)
![License](https://img.shields.io/badge/License-MIT-brown)

A bot to help you convert different timezones inside messages in **Discord**/**Slack**/**Telegram**.This bot doesnt interfere with other messages in the channel so its perfect for big servers.

## What it does

Got teammates in different time zones? This bot helps you figure out what time it is for everyone.

- **Type a time**, get it converted to your timezone
- **React with a clock emoji** on Discord to convert any message
- **Works the same way** on Discord, Slack, and Telegram
- **Remembers your timezone** once you set it

## Add the bot to your platform

| Platform | Link | 
|----------|------|
| Discord | [![Add to Discord](https://img.shields.io/badge/Add%20to-Discord-7289DA?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/oauth2/authorize?client_id=1392192666053251143&permissions=8&integration_type=0&scope=bot+applications.commands) |
| Slack | [![Add to Slack](https://img.shields.io/badge/Add%20to-Slack-4A154B?style=for-the-badge&logo=slack&logoColor=white)](https://slack.com/oauth/v2/authorize?client_id=9180592732466.9175325235619&scope=channels:read,chat:write,app_mentions:read,channels:history,groups:history,im:history,commands&user_scope=) |
| Telegram | [![Start Telegram](https://img.shields.io/badge/Start-Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/TimeZone123Bot) |

## How to use it

1. **Set your timezone** (only need to do this once):
   ```
   /timezone EST
   /timezone Europe/London
   /timezone UTC+5:30
   ```

2. **Convert times**:
   ```
   /time "Meeting at 3 PM GMT"
   /time "Call at 2:30 PM EST"
   ```

3. **On Discord**: React to any message with ⏰ 🕐 ⏳ or ⏱️ to get a private message with the time conversion

## Examples

**Someone says**: "Daily standup at 9 AM EST tomorrow"  
**Bot replies**: "9:00AM EST → 2:00PM GMT → 6:00AM PST"

**Someone says**: "Product launch at 15:00 UTC on Friday"  
**Bot replies**: "3:00PM UTC → 11:00AM EDT → 8:00AM PDT (Friday, March 15th)"

## Running it yourself

Want to run your own version? Here's what you need:

### Requirements
- Node.js (for Discord bot)
- Python 3.8+ (for Slack and Telegram bots)

### Discord Bot
```bash
cd Discord/
npm install
cp .env.example .env    # Add your Discord bot token
npm run register        # Register commands with Discord
npm run dev
```

### Slack Bot  
```bash
cd Slack/
pip install -r requirements.txt
cp .env.example .env    # Add your Slack tokens
python app.py
```

### Telegram Bot
```bash
cd Telegram/
pip install -r requirements.txt  
cp .env.example .env    # Add your Telegram bot token
python app.py
```

## Project structure

```
timezone-bot/
├── Discord/           # Discord bot (Node.js)
├── Slack/            # Slack bot (Python)  
├── Telegram/         # Telegram bot (Python)
└── shared/           # Shared config files
    ├── timezones.json
    ├── user_preferences.json
    └── response_messages.json
```

## Contributing

Want to help? Great!

1. Fork the repo
2. Make your changes
3. Test them
4. Submit a pull request

## License

MIT License - do whatever you want with it.