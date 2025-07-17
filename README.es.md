# Bot de Zonas Horarias

![Typescript](https://img.shields.io/badge/Typescript-3178C6?logo=Typescript&logoColor=white)
![Python](https://img.shields.io/badge/Python-yellow?logo=Python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-307387?logo=flask&logoColor=white)
![Node.js](https://img.shields.io/badge/NodeJS-339933?logo=nodedotjs&logoColor=white)
![Express](https://img.shields.io/badge/Express-000000?logo=express&logoColor=white)
![Field](https://img.shields.io/badge/Field-Bots-white)
![License](https://img.shields.io/badge/License-MIT-brown)

Un bot para ayudarte a convertir zonas horarias dentro de mensajes en **Discord**/**Slack**/**Telegram**. Este bot no interfiere con otros mensajes en el canal, por lo que es perfecto para servidores grandes.

## Plataformas Disponibles
| Discord | Slack | Telegram |
|---------|-------|----------|
| [![Agregar a Discord](https://img.shields.io/badge/Add%20to-Discord-7289DA?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/oauth2/authorize?client_id=1392192666053251143&permissions=8&integration_type=0&scope=bot+applications.commands) <img src="Discord.png" alt="Discord Bot" width="200" height="150"> | [![Agregar a Slack](https://img.shields.io/badge/Add%20to-Slack-4A154B?style=for-the-badge&logo=slack&logoColor=white)](https://slack.com/oauth/v2/authorize?client_id=9180592732466.9175325235619&scope=channels:read,chat:write,app_mentions:read,channels:history,groups:history,im:history,commands&user_scope=) <img src="Slack.png" alt="Slack Bot" width="200" height="150"> | [![Iniciar Telegram](https://img.shields.io/badge/Start-Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/TimeZone123Bot) <img src="Telegram.png" alt="Telegram Bot" width="200" height="150"> |

## ¿Qué hace?

Imagina esto: estás coordinando una reunión con compañeros de equipo en tres continentes. Alguien dice "nos vemos a las 3pm EST" y de repente todos están haciendo cálculos mentales. Tu colega en Londres calcula GMT, tu compañero en Tokio piensa en JST, y tú solo intentas recordar si estás en PST o PDT.

Este bot resuelve ese problema. Vive silenciosamente en tus servidores de Discord, espacios de trabajo de Slack y chats de Telegram, esperando a que lo uses, y cuando lo haces, muestra mensajes efímeros para no interrumpir la conversación ni saturar el canal.

**¿Cómo funciona?**
- Alguien escribe `/time 3pm EST` o simplemente menciona una hora en la conversación
- En Discord, cualquiera puede reaccionar con ⏰ a cualquier mensaje que contenga una hora
- El bot responde de forma privada con conversiones a tu zona horaria y otras zonas populares
- Recuerda tu preferencia de zona horaria en todas las plataformas
- Soporta más de 200 alias de zonas horarias (EST, PST, GMT, JST, etc.)

**Ejemplo de conversación:**
```
Alice: "La daily es a las 9am PST mañana"
[Alguien reacciona con ⏰]
Bot (privado): 🕒 9:00 AM PST
                🌍 Tu zona horaria: 12:00 PM EST  
                🌏 UTC: 5:00 PM
                🌍 Londres: 5:00 PM GMT
```

## Ejecutarlo tú mismo

¿Quieres correr tu propia versión? Así funciona cada plataforma:

### Requisitos

Antes de entrar en la configuración específica de cada plataforma, necesitarás diferente infraestructura según los bots que quieras ejecutar:

**Para los bots de Discord y Slack:**
- Un servidor con IP pública o nombre de dominio
- Soporte HTTPS (requerido para webhooks)
- Acceso a puertos para solicitudes entrantes (Discord usa webhooks, Slack usa Socket Mode pero OAuth requiere endpoints)
- Considera servicios como Railway, Heroku, DigitalOcean o AWS para el hosting

**Para el bot de Telegram:**
- ¡No se requiere servidor! Telegram usa polling, así que puede ejecutarse desde tu máquina local
- Solo necesita conexión a internet para recibir actualizaciones

**Requisitos generales:**
- Node.js 16+ (para el bot de Discord)
- Python 3.8+ (para los bots de Slack y Telegram)
- Tokens de bot y credenciales API de cada plataforma:
  - **Discord**: [Portal de Desarrolladores de Discord](https://discord.com/developers/applications)
  - **Slack**: [Panel de Slack API](https://api.slack.com/apps)
  - **Telegram**: [@BotFather](https://t.me/BotFather) en Telegram

### Configuración del Bot de Discord
```bash
cd Discord/
npm install                 # Instala express, discord-interactions, ws, moment-timezone
cp .env.example .env       # Copia la plantilla de entorno y rellénala con tus tokens
npm run register           # Registra los comandos slash con la API de Discord
npm run dev               # Inicia el servidor Express en el puerto 8943
```
> 💡 **Consejo**: Copia `.env.example` a `.env` y rellena tus credenciales del bot de Discord desde el [Portal de Desarrolladores de Discord](https://discord.com/developers/applications)

### Configuración del Bot de Slack
```bash
cd Slack/
pip install -r requirements.txt  # Instala slack-bolt, flask, pytz
cp .env.example .env             # Copia la plantilla de entorno y rellénala con tus tokens
python oauth_server.py           # Inicia el servidor OAuth (puerto 8944)
python app.py                    # Inicia el bot principal (puerto 8945)
```
> 💡 **Consejo**: Copia `.env.example` a `.env` y rellena tus credenciales de Slack desde el [Panel de Slack API](https://api.slack.com/apps)

### Configuración del Bot de Telegram  
```bash
cd Telegram/
pip install -r requirements.txt  # Instala pyTelegramBotAPI, pytz
cp .env.example .env             # Copia la plantilla de entorno y rellénala con tu token
python app.py                    # Inicia el bot con long polling
python web_server.py             # Inicia el servidor web (puerto 8946)
```
> 💡 **Consejo**: Copia `.env.example` a `.env` y rellena tu token de bot desde [@BotFather](https://t.me/BotFather) en Telegram

## Arquitectura Técnica

Conversión unificada de zonas horarias en tres plataformas usando una capa de datos compartida.

### Pipeline de zonas horarias

1. **Análisis de texto**: Regex detecta expresiones de tiempo (`3pm`, `15:00`, `3:30 PM EST`)
2. **Resolución de zona horaria**: Mapea alias a identificadores IANA (`EST` → `America/New_York`)
3. **Conversión**: `moment-timezone` (Node.js) o `pytz` (Python)

#### **Discord** (`Discord/`): Servidor Express + WebSocket para comandos slash y reacciones ⏰  
```bash
├── bot.js           # Lógica principal del bot, servidor Express, manejo de WebSocket
├── register.js      # Registro único de comandos slash
├── package.json     # Dependencias: express, discord-interactions, ws
└── .env.example     # Token del bot de Discord, credenciales de la app
```

#### **Slack** (`Slack/`): Doble proceso Socket Mode + servidor OAuth con Flask  
```bash
├── app.py           # Bot principal usando Slack Bolt SDK
├── oauth_server.py  # Servidor OAuth con Flask para instalación en workspaces
├── requirements.txt # Dependencias: slack-bolt, flask, pytz
└── .env.example     # Tokens del bot/app de Slack, signing secret
```
#### **Telegram** (`Telegram/`): Proceso único con long polling
```bash
├── app.py           # Implementación completa del bot con polling
├── requirements.txt # Dependencias: pyTelegramBotAPI, pytz  
└── .env.example     # Solo token del bot de Telegram
```

#### Datos Compartidos (`shared/`)

```json
// timezones.json - Más de 200 alias de zonas horarias
{
  "aliases": { "EST": "America/New_York" },
  "popular": ["UTC", "America/New_York", "Europe/London"]
}

// user_preferences.json - Zonas horarias de usuarios multiplataforma
{
  "discord": {"user_id": "timezone"},
  "slack": {"user_id": "timezone"},
  "telegram": {"user_id": "timezone"}
}
```

**¿Por qué archivos JSON?**: Sin dependencias de base de datos para auto-hospedaje

## Contribuir

¿Quieres ayudar a que la coordinación de zonas horarias sea más fácil para todos?

1. **Haz un fork del repo** - Empieza con tu propia copia
2. **Elige una plataforma** - Cada una tiene su propio entorno de desarrollo
3. **Haz tus cambios** - Sigue los patrones existentes y prueba localmente
4. **Prueba en todas las plataformas** - Asegúrate de que los cambios en datos compartidos funcionen en todas
5. **Envía un pull request** - Revisaremos y fusionaremos

La belleza de esta arquitectura es que puedes contribuir a una plataforma sin necesidad de entender las otras. Los archivos de datos compartidos aseguran la consistencia en todas las implementaciones.

## Licencia

Licencia MIT - haz lo que quieras con ella. (Ver archivo LICENSE para más detalles.)
