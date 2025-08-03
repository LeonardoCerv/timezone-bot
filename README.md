
> 📖 🇪🇸 También disponible en español: [README.es.md](README.es.md)

# Timezone Bot

![Typescript](https://img.shields.io/badge/Typescript-3178C6?logo=Typescript&logoColor=white)
![Python](https://img.shields.io/badge/Python-yellow?logo=Python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-307387?logo=flask&logoColor=white)
![Node.js](https://img.shields.io/badge/NodeJS-339933?logo=nodedotjs&logoColor=white)
![Express](https://img.shields.io/badge/Express-000000?logo=express&logoColor=white)
![Field](https://img.shields.io/badge/Field-Bots-white)
![License](https://img.shields.io/badge/License-MIT-brown)

This bot was created with the intent of making timezone convertion easier and faster inside messages in **Discord**/**Slack**/**Telegram**.

## Available Platforms
| Discord | Slack | Telegram |
|---------|-------|----------|
| [![Add to Discord](https://img.shields.io/badge/Add%20to-Discord-7289DA?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/oauth2/authorize?client_id=1392192666053251143&permissions=8&integration_type=0&scope=bot+applications.commands) <img src="Discord.png" alt="Discord Bot" width="200" height="150"> | [![Add to Slack](https://img.shields.io/badge/Add%20to-Slack-4A154B?style=for-the-badge&logo=slack&logoColor=white)](https://slack.com/oauth/v2/authorize?client_id=9180592732466.9175325235619&scope=channels:read,chat:write,app_mentions:read,channels:history,groups:history,im:history,commands&user_scope=) <img src="Slack.png" alt="Slack Bot" width="200" height="150"> | [![Start Telegram](https://img.shields.io/badge/Start-Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/TimeZone123Bot) <img src="Telegram.png" alt="Telegram Bot" width="200" height="150"> |

## What it does


This bot responds to the following commands:

| Command                  | Description                                                                                  |
|--------------------------|----------------------------------------------------------------------------------------------|
| `/time <time> <zone>`    | Converts the given time in the specified timezone to your local timezone and popular zones.  |
| `/settimezone <zone>`    | Sets your preferred timezone for future conversions.                                         |
| `/mytimezone`            | Displays your currently saved timezone.                                                      |
| `/help`                  | Shows help and usage instructions for the bot.                                               |
| React with ⏰ (Discord)   | Triggers a private message with time conversions for the mentioned time in the message.      |

it always replies with ephemeral messages with the intention of not interfering with the conversation in the channels.

## Running it yourself

If you want to run a local version of the bot heres what you need to know:

### Requirements

**General requirements:**
- Node.js 16+ (for Discord bot)
- Python 3.8+ (for Slack and Telegram bots)
- Bot tokens and API credentials from each platform:
  - **Discord**: [Discord Developer Portal](https://discord.com/developers/applications)
  - **Slack**: [Slack API Dashboard](https://api.slack.com/apps)
  - **Telegram**: [@BotFather](https://t.me/BotFather) on Telegram

> After downloading or cloning this repo you can now go ahead and dive into each platform

### Discord Bot Setup
inside the /Discord directory:
```bash
npm install
cp .env.example .env #fill with your data
npm run register
npm run dev
```
> **Remember to**: Copy `.env.example` to `.env` and fill in your Discord bot credentials from the [Discord Developer Portal](https://discord.com/developers/applications)

### Slack Bot Setup
inside the /Slack directory:
```bash
cd Slack/
pip install -r requirements.txt
cp .env.example .env
python oauth_server.py
python app.py
```
> **Remember to**: Copy `.env.example` to `.env` and fill in your Slack app credentials from the [Slack API Dashboard](https://api.slack.com/apps)

### Telegram Bot Setup  
inside the /Telegram directory:
```bash
pip install -r requirements.txt
cp .env.example .env
python app.py
python web_server.py
```
> **Remember to**: Copy `.env.example` to `.env` and fill in your bot token from [@BotFather](https://t.me/BotFather) on Telegram

## License

this project is under the MIT License, see LICENSE.md for more info