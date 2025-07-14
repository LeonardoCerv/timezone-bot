# Timezone Bot

![Typescript](https://img.shields.io/badge/Typescript-3178C6?logo=Typescript&logoColor=white)
![Python](https://img.shields.io/badge/Python-yellow?logo=Python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-307387?logo=flask&logoColor=white)
![Node.js](https://img.shields.io/badge/NodeJS-339933?logo=nodedotjs&logoColor=white)
![Express](https://img.shields.io/badge/Express-000000?logo=express&logoColor=white)
![Field](https://img.shields.io/badge/Field-Bots-white)
![License](https://img.shields.io/badge/License-MIT-brown)

Un bot para ayudarte a convertir diferentes zonas horarias dentro de mensajes en **Discord**/**Slack**/**Telegram**. Este bot no interfiere con otros mensajes en el canal, por lo que es perfecto para servidores grandes.

## Qué hace

¿Tienes compañeros en diferentes zonas horarias? Este bot te ayuda a saber qué hora es para cada uno.

- **Escribe una hora**, y la convierte a tu zona horaria
- **Reacciona con un emoji de reloj** en Discord para convertir cualquier mensaje
- **Funciona igual** en Discord, Slack y Telegram
- **Recuerda tu zona horaria** una vez que la configuras

[![Agregar a Discord](https://img.shields.io/badge/Agregar%20a-Discord-7289DA?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/oauth2/authorize?client_id=1392192666053251143&permissions=8&integration_type=0&scope=bot+applications.commands)
[![Agregar a Slack](https://img.shields.io/badge/Agregar%20a-Slack-4A154B?style=for-the-badge&logo=slack&logoColor=white)](https://slack.com/oauth/v2/authorize?client_id=9180592732466.9175325235619&scope=channels:read,chat:write,app_mentions:read,channels:history,groups:history,im:history,commands&user_scope=)
[![Iniciar Telegram](https://img.shields.io/badge/Iniciar-Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/TimeZone123Bot)

## Ejecutarlo tú mismo

¿Quieres ejecutar tu propia versión? Sigue estos pasos:

### Configuración del bot de Discord
```bash
cd Discord/
npm install                 # Instala express, discord-interactions, ws, moment-timezone
cp .env.example .env        # Copia la plantilla de entorno y rellénala con tus tokens
npm run register            # Registra los comandos slash con la API de Discord
npm run dev                 # Inicia el servidor Express en el puerto 3000
```
> 💡 **Consejo de configuración**: Copia `.env.example` a `.env` y rellena tus credenciales del bot de Discord desde el [Portal de Desarrolladores de Discord](https://discord.com/developers/applications)

### Configuración del bot de Slack
```bash
cd Slack/
pip install -r requirements.txt  # Instala slack-bolt, flask, pytz
cp .env.example .env             # Copia la plantilla de entorno y rellénala con tus tokens
python oauth_server.py           # Inicia el servidor OAuth (puerto 8944)
python app.py                    # Inicia el bot principal (proceso separado)
```
> 💡 **Consejo de configuración**: Copia `.env.example` a `.env` y rellena tus credenciales de la app de Slack desde el [Panel de API de Slack](https://api.slack.com/apps)

### Configuración del bot de Telegram  
```bash
cd Telegram/
pip install -r requirements.txt  # Instala pyTelegramBotAPI, pytz
cp .env.example .env             # Copia la plantilla de entorno y rellénala con tu token
python app.py                    # Inicia el bot con long polling
```
> 💡 **Consejo de configuración**: Copia `.env.example` a `.env` y rellena tu token de bot desde [@BotFather](https://t.me/BotFather) en Telegram

## Cómo funciona técnicamente

### Lógica central de zonas horarias
Todas las plataformas usan el mismo algoritmo de conversión de zonas horarias:

1. **Analiza la hora del texto** usando patrones regex (soporta formatos 12/24h, AM/PM, zonas horarias)
2. **Resuelve alias de zonas horarias** vía `timezones.json` compartido (EST→America/New_York, etc.)
3. **Convierte usando librerías de zonas horarias**:
    - Node.js: `moment-timezone`
    - Python: `pytz` 
4. **Formatea la salida** mostrando hora original → zona horaria del usuario → 2-3 zonas populares

### Implementación específica por plataforma

**Discord**: 
- Comandos slash (`/time`, `/timezone`) gestionados vía webhook de Express
- Conversión por reacción usa WebSocket para detectar reacciones de emoji ⏰
- Respuestas privadas para evitar spam en el canal

**Slack**:
- Conexión Socket Mode gestiona eventos en tiempo real (menciones, DMs, comandos slash)
- Servidor OAuth separado en Flask para instalaciones en workspace
- Soporte de hilos para mantener el contexto de la conversación

**Telegram**:
- Long polling revisa continuamente nuevos mensajes
- Soporta comandos inline y mensajes directos
- Sin OAuth - autenticación simple por token de bot

### Gestión de datos compartidos
- **Preferencias de usuario**: Archivo JSON almacena zona horaria por ID de usuario en todas las plataformas
- **Alias de zonas horarias**: Más de 200 abreviaturas comunes mapeadas a nombres IANA
- **Consistencia multiplataforma**: Misma lógica y formato de respuesta en todas partes

## Arquitectura y frameworks

Este proyecto usa diferentes frameworks para cada plataforma, optimizados para sus APIs y ecosistemas:

### Bot de Discord (Node.js/Express)
- **Framework**: Express.js con Discord.js Interactions
- **Lenguaje**: JavaScript (ES6 modules)
- **Librerías clave**: 
  - `discord-interactions` - Gestiona comandos slash y mensajes de Discord
  - `express` - Servidor HTTP para webhooks de Discord
  - `ws` - Soporte WebSocket para eventos en tiempo real
  - `moment-timezone` - Lógica de conversión de zonas horarias
- **Arquitectura**: API basada en interacciones de Discord con webhooks para comandos slash y WebSocket para eventos de reacción
- **Estructura de archivos**:
  - `bot.js` - Lógica principal del bot con servidor Express y manejadores de eventos
  - `register.js` - Registra comandos slash con la API de Discord

### Bot de Slack (Python/Flask + Slack Bolt)
- **Framework**: Flask para OAuth + Slack Bolt para funcionalidad del bot  
- **Lenguaje**: Python 3.8+
- **Librerías clave**:
  - `slack-bolt` - SDK oficial de Slack para apps con socket mode
  - `flask` - Framework web para OAuth y endpoints webhook
  - `pytz` - Manejo de zonas horarias en Python
- **Arquitectura**: Configuración de doble servidor:
  - `app.py` - Bot principal usando Socket Mode para eventos en tiempo real
  - `oauth_server.py` - Servidor Flask separado para flujo de instalación OAuth
- **Por qué esta configuración**: Slack requiere OAuth para instalación en workspace, mientras Bolt gestiona la mensajería en tiempo real

### Bot de Telegram (Python/pyTelegramBotAPI)
- **Framework**: pyTelegramBotAPI (telebot)
- **Lenguaje**: Python 3.8+
- **Librerías clave**:
  - `pyTelegramBotAPI` - Wrapper ligero para la API de bots de Telegram
  - `pytz` - Conversiones de zonas horarias
- **Arquitectura**: Bot simple basado en polling que procesa actualizaciones directamente de la API de Telegram
- **Estructura de archivos**: Un solo archivo `app.py` - implementación más simple ya que la API de Telegram es directa

### Componentes compartidos
Todas las plataformas comparten configuración y datos:
- **timezones.json** - Más de 200 alias de zonas horarias y zonas populares
- **user_preferences.json** - Preferencias de zona horaria por usuario (Discord/Slack/Telegram)
- **response_messages.json** - Respuestas estandarizadas con formato específico por plataforma

### ¿Por qué diferentes frameworks?

1. **Discord (Node.js/Express)**: 
    - La API de Discord está optimizada para JavaScript/WebSocket
    - Express gestiona comandos slash vía webhooks eficientemente
    - Eventos de reacción en tiempo real requieren conexión WebSocket

2. **Slack (Python/Flask + Bolt)**:
    - Slack Bolt SDK ofrece manejo robusto de eventos y middleware
    - Flask necesario para el flujo OAuth (instalación en workspace)
    - Socket Mode elimina la necesidad de webhooks públicos

3. **Telegram (Python/telebot)**:
    - API más simple de las tres plataformas
    - Sin OAuth - autenticación directa por token
    - Polling funciona perfectamente para conversión de zonas horarias


## Estructura del proyecto

```
timezone-bot/
├── Discord/           # Bot de Discord (Node.js + Express)
│   ├── bot.js        # Lógica principal + servidor Express
│   ├── register.js   # Registro de comandos slash
│   └── package.json  # Dependencias: express, discord-interactions, ws
├── Slack/            # Bot de Slack (Python + Flask + Bolt)
│   ├── app.py        # Bot principal usando Slack Bolt SDK
│   ├── oauth_server.py # Servidor Flask para instalación OAuth
│   └── requirements.txt # Dependencias: slack-bolt, flask, pytz
├── Telegram/         # Bot de Telegram (Python + pyTelegramBotAPI)
│   ├── app.py        # Lógica principal del bot
│   └── requirements.txt # Dependencias: pyTelegramBotAPI, pytz
└── shared/           # Datos compartidos multiplataforma
     ├── timezones.json      # Alias de zonas horarias y zonas populares
     ├── user_preferences.json # Preferencias de zona horaria por usuario
     └── response_messages.json # Respuestas estandarizadas
```

## Contribuir

¿Quieres ayudar? ¡Genial!

1. Haz un fork del repositorio
2. Realiza tus cambios
3. Prueba tus cambios
4. Envía un pull request

## Licencia

Licencia MIT - haz lo que quieras con ella.