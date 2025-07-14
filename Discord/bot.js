import 'dotenv/config';
import express from 'express';
import WebSocket from 'ws';
import moment from 'moment-timezone';
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { join } from 'path';
import {
  InteractionResponseFlags,
  InteractionResponseType,
  InteractionType,
  verifyKeyMiddleware,
} from 'discord-interactions';

// File paths
const USER_PREFS_PATH = join(process.cwd(), '../shared/user_preferences.json');
const SHARED_TIMEZONES_PATH = join(process.cwd(), '../shared/timezones.json');
const RESPONSE_MESSAGES_PATH = join(process.cwd(), '../shared/response_messages.json');

// Load shared timezone config
let timezoneConfig = { aliases: {}, popular: [] };
try {
  if (existsSync(SHARED_TIMEZONES_PATH)) {
    const data = readFileSync(SHARED_TIMEZONES_PATH, 'utf8');
    timezoneConfig = JSON.parse(data);
  }
} catch (error) {
  console.error('Failed to load timezone config:', error);
}

// Load shared response messages
let responseMessages = {};
try {
  if (existsSync(RESPONSE_MESSAGES_PATH)) {
    const data = readFileSync(RESPONSE_MESSAGES_PATH, 'utf8');
    responseMessages = JSON.parse(data);
  }
} catch (error) {
  console.error('Failed to load response messages:', error);
}

// Database functions
function initUserPrefs() {
  if (!existsSync(USER_PREFS_PATH)) {
    writeFileSync(USER_PREFS_PATH, JSON.stringify({ discord: {}, slack: {}, telegram: {} }, null, 2));
  }
}

function readUserPrefs() {
  try {
    if (!existsSync(USER_PREFS_PATH)) {
      initUserPrefs();
    }
    const data = readFileSync(USER_PREFS_PATH, 'utf8');
    const fullData = JSON.parse(data);
    return { users: fullData.discord || {} };
  } catch (error) {
    console.error('Error reading user preferences:', error);
    return { users: {} };
  }
}

function writeUserPrefs(data) {
  try {
    // Read existing data first
    let fullData = { discord: {}, slack: {}, telegram: {} };
    if (existsSync(USER_PREFS_PATH)) {
      const existing = readFileSync(USER_PREFS_PATH, 'utf8');
      fullData = JSON.parse(existing);
    }
    
    // Update only the discord section
    fullData.discord = data.users || {};
    
    writeFileSync(USER_PREFS_PATH, JSON.stringify(fullData, null, 2));
    return true;
  } catch (error) {
    console.error('Error writing user preferences:', error);
    return false;
  }
}

// Timezone utilities
function normalizeTimezone(input) {
  if (!input) return null;
  
  // Check aliases first
  const alias = timezoneConfig.aliases[input.toUpperCase()];
  if (alias) return alias;
  
  // Check if it's a valid moment timezone
  if (moment.tz.zone(input)) return input;
  
  // Handle UTC offset formats (UTC-5, UTC+3:30)
  const offsetMatch = input.match(/^(UTC)?([+-]\d{1,2}):?(\d{2})?$/i);
  if (offsetMatch) {
    const sign = offsetMatch[2].startsWith('+') ? '+' : '-';
    const hours = Math.abs(parseInt(offsetMatch[2]));
    const minutes = offsetMatch[3] ? parseInt(offsetMatch[3]) : 0;
    
    if (hours <= 14 && minutes <= 59) {
      // Etc/GMT offsets are inverted
      return `Etc/GMT${sign === '+' ? '-' : '+'}${hours}`;
    }
  }
  
  return null;
}

function setUserTimezone(userId, timezone) {
  const normalizedTz = normalizeTimezone(timezone);
  if (!normalizedTz) return false;
  
  const data = readUserPrefs();
  data.users[userId] = {
    timezone: normalizedTz,
    displayName: timezone,
    lastUpdated: new Date().toISOString()
  };
  return writeUserPrefs(data);
}

function getUserTimezone(userId) {
  const data = readUserPrefs();
  return data.users?.[userId]?.timezone || null;
}

// Time parsing and conversion
function extractTimes(content) {
  const patterns = [
    // With timezone: "3:00 PM EST", "2 PM PST", "3 PM SGT"
    /\b(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)\s*([A-Z]{2,4}|UTC[+-]\d{1,2}:?\d{0,2}|GMT[+-]\d{1,2}:?\d{0,2})\b/gi,
    /\b(\d{1,2})\s*(AM|PM|am|pm)\s*([A-Z]{2,4}|UTC[+-]\d{1,2}:?\d{0,2}|GMT[+-]\d{1,2}:?\d{0,2})\b/gi,
    // 12-hour: "3:00 PM", "3 PM"
    /\b(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)\b/gi,
    /\b(\d{1,2})\s*(AM|PM|am|pm)\b/gi,
    // 24-hour: "15:30", "09:00"
    /\b([01]?\d|2[0-3]):([0-5]\d)\b/g,
    // With context: "at 3pm"
    /\b(at|around|by|before|after)\s+(\d{1,2}):?(\d{2})?\s*(AM|PM|am|pm)?\b/gi,
  ];
  
  const times = [];
  const spans = [];
  
  patterns.forEach(pattern => {
    let match;
    while ((match = pattern.exec(content)) !== null) {
      const start = match.index;
      const end = match.index + match[0].length;
      
      // Skip overlapping matches
      const overlaps = spans.some(span => 
        (start >= span.start && start < span.end) ||
        (end > span.start && end <= span.end) ||
        (start <= span.start && end >= span.end)
      );
      
      if (!overlaps) {
        times.push(match[0].trim());
        spans.push({ start, end });
      }
    }
  });
  
  return times
    .filter(time => time.length >= 2 && !/^\d{1,2}$/.test(time.trim()))
    .sort((a, b) => content.indexOf(a) - content.indexOf(b));
}

function parseTime(timeStr, contextTz = 'UTC') {
  if (!timeStr) return null;
  
  let timezone = contextTz;
  
  // Look for timezone in string - improved regex to catch more formats, excluding AM/PM
  const tzMatch = timeStr.match(/\b(?!AM|PM)([A-Z]{2,4}|UTC[+-]\d{1,2}:?\d{0,2}|GMT[+-]\d{1,2}:?\d{0,2})\b/i);
  if (tzMatch) {
    const tzCandidate = tzMatch[1];
    // Double-check it's not AM/PM
    if (!/^(AM|PM)$/i.test(tzCandidate)) {
      const normalizedTz = normalizeTimezone(tzCandidate);
      if (normalizedTz) timezone = normalizedTz;
    }
  }
  
  // Clean up time string
  const cleanTime = timeStr
    .replace(/\b(at|around|by|before|after)\s+/gi, '')
    .replace(/\b([A-Z]{2,4}|UTC[+-]\d{1,2}:?\d{0,2}|GMT[+-]\d{1,2}:?\d{0,2})\b/gi, '')
    .trim();
  
  // Try different formats
  const formats = ['h:mm A', 'h A', 'HH:mm', 'H:mm', 'h:mm:ss A', 'HH:mm:ss'];
  
  for (const format of formats) {
    const parsed = moment.tz(cleanTime, format, timezone);
    if (parsed.isValid()) {
      return { moment: parsed, timezone };
    }
  }
  
  // Last resort
  const fallback = moment.tz(cleanTime, timezone);
  return fallback.isValid() ? { moment: fallback, timezone } : null;
}

// Helper function to get display name for timezone
function getTimezoneDisplayName(timezone) {
  // Check if we have a display name in the timezone config
  if (timezoneConfig.display_names && timezoneConfig.display_names[timezone]) {
    return timezoneConfig.display_names[timezone];
  }
  
  // Fallback to moment timezone abbreviation
  const momentTz = moment.tz(timezone);
  return momentTz.format('z');
}

function convertTimes(content, targetTimezone) {
  const foundTimes = extractTimes(content);
  if (foundTimes.length === 0) return [];
  
  const results = [];
  
  for (const timeStr of foundTimes) {
    // Try to parse with timezone from string, fallback to UTC only if no TZ found
    const parsed = parseTime(timeStr);
    if (parsed) {
        const converted = parsed.moment.clone().tz(targetTimezone);
        const isSameDay = parsed.moment.format('YYYY-MM-DD') === converted.format('YYYY-MM-DD');
        
        // Format consistently with proper timezone abbreviations
        const originalFormatted = `${parsed.moment.format('h:mmA')} ${getTimezoneDisplayName(parsed.timezone)}`;
        const convertedFormatted = `${converted.format('h:mmA')} ${getTimezoneDisplayName(targetTimezone)}`;
        
        results.push({
          original: originalFormatted,
          converted: convertedFormatted,
          date: converted.format('dddd, MMMM Do'),
          isSameDay
        });
    }
  }
  
  return results;
}

// Discord API utilities
async function sendDM(userId, content) {
  try {
    // Create DM channel
    const dmResponse = await fetch('https://discord.com/api/v10/users/@me/channels', {
      method: 'POST',
      headers: {
        'Authorization': `Bot ${process.env.DISCORD_TOKEN}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ recipient_id: userId })
    });
    
    if (!dmResponse.ok) return false;
    const dmChannel = await dmResponse.json();
    
    // Send message
    const messageResponse = await fetch(`https://discord.com/api/v10/channels/${dmChannel.id}/messages`, {
      method: 'POST',
      headers: {
        'Authorization': `Bot ${process.env.DISCORD_TOKEN}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ content })
    });
    
    return messageResponse.ok;
  } catch (error) {
    console.error('Failed to send DM:', error);
    return false;
  }
}

async function getMessage(channelId, messageId) {
  try {
    const response = await fetch(`https://discord.com/api/v10/channels/${channelId}/messages/${messageId}`, {
      headers: {
        'Authorization': `Bot ${process.env.DISCORD_TOKEN}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) return null;
    const message = await response.json();
    return message.content;
  } catch (error) {
    console.error('Failed to get message:', error);
    return null;
  }
}

// Gateway client for reactions
class GatewayClient {
  constructor() {
    this.ws = null;
    this.heartbeatInterval = null;
    this.sequenceNumber = null;
    this.timeEmojis = ['⏰', '⏳', '⏱️', '🕐', '🕑', '🕒', '🕓', '🕔', '🕕', '🕖', '🕗', '🕘', '🕙', '🕚', '🕛'];
  }

  connect() {
    this.ws = new WebSocket('wss://gateway.discord.gg/?v=10&encoding=json');
    
    this.ws.on('open', () => console.log('Connected to Discord Gateway'));
    this.ws.on('message', (data) => this.handleMessage(JSON.parse(data)));
    this.ws.on('close', (code) => {
      console.log(`Gateway closed: ${code}`);
      this.cleanup();
    });
    this.ws.on('error', (error) => console.error('Gateway error:', error));
  }

  cleanup() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  handleMessage(message) {
    const { op, d, s, t } = message;
    
    if (s) this.sequenceNumber = s;

    switch (op) {
      case 10: // Hello
        this.startHeartbeat(d.heartbeat_interval);
        this.identify();
        break;
      case 0: // Dispatch
        if (t === 'MESSAGE_REACTION_ADD') this.handleReaction(d);
        break;
      case 1: // Heartbeat request
        this.sendHeartbeat();
        break;
    }
  }

  startHeartbeat(interval) {
    this.heartbeatInterval = setInterval(() => this.sendHeartbeat(), interval);
  }

  sendHeartbeat() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ op: 1, d: this.sequenceNumber }));
    }
  }

  identify() {
    const payload = {
      op: 2,
      d: {
        token: process.env.DISCORD_TOKEN,
        intents: (1 << 0) | (1 << 10) | (1 << 15) | (1 << 12), // Basic intents for reactions
        properties: {
          os: process.platform,
          browser: 'timezone-bot',
          device: 'timezone-bot'
        }
      }
    };

    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(payload));
    }
  }

  async handleReaction(data) {
    const { user_id, channel_id, message_id, emoji, member } = data;
    
    if (member?.user?.bot || !this.timeEmojis.includes(emoji.name)) return;

    const userTimezone = getUserTimezone(user_id);
    const messageContent = await getMessage(channel_id, message_id);
    
    if (!messageContent) return;

    if (!userTimezone) {
      await sendDM(user_id, responseMessages.errors?.no_timezone_set || "No timezone set. Use `/timezone EST` to set one");
      return;
    }

    const conversions = convertTimes(messageContent, userTimezone);
    if (conversions.length === 0) {
      await sendDM(user_id, responseMessages.errors?.no_times_found || "*No times found. Use format: /convert 3:00PM EST*");
      return;
    }

    let response = (responseMessages.success?.conversion_header || "**Times in your timezone ({timezone})**\n\n").replace('{timezone}', userTimezone);
    response += `Original message: ${messageContent}\n\n`;
    
    for (const conv of conversions) {
      const template = conv.isSameDay 
        ? (responseMessages.success?.conversion_line || "**{original}** → **{converted}**")
        : (responseMessages.success?.conversion_line_with_date || "**{original}** → **{converted}** ({date})");
      
      const line = template
        .replace('{original}', conv.original)
        .replace('{converted}', conv.converted)
        .replace('{date}', conv.date);
      response += `${line}\n`;
    }
    
    response += `\n*From <#${channel_id}>*`;
    await sendDM(user_id, response);
  }

  disconnect() {
    this.cleanup();
    this.ws?.close(1000);
  }
}

// Express app setup
const app = express();
const PORT = process.env.PORT || 3000;
app.use(express.json());

function createResponse(message, ephemeral = true) {
  return {
    type: InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
    data: {
      flags: ephemeral ? InteractionResponseFlags.EPHEMERAL : undefined,
      content: message
    }
  };
}

// Discord interactions endpoint
app.post('/interactions', verifyKeyMiddleware(process.env.PUBLIC_KEY), (req, res) => {
  const { type, data } = req.body;

  if (type === InteractionType.PING) {
    return res.send({ type: InteractionResponseType.PONG });
  }

  if (type === InteractionType.APPLICATION_COMMAND) {
    const { name } = data;
    const { user, member } = req.body;
    const userId = req.body.context === 0 ? member.user.id : user.id;

    if (name === 'timezone') {
      const timezone = data.options[0].value;
      
      if (!normalizeTimezone(timezone)) {
        return res.send(createResponse(responseMessages.errors?.invalid_timezone || "*Invalid timezone. Use format: /convert 3:00PM EST*"));
      }
      
      const success = setUserTimezone(userId, timezone);
      
      if (success) {
        const tz = moment.tz(normalizeTimezone(timezone));
        const currentTime = tz.format('h:mm A z');
        const message = (responseMessages.success?.timezone_set || "Timezone set to `{timezone}`\nCurrent time: **{time}**")
          .replace('{timezone}', timezone)
          .replace('{time}', currentTime);
        return res.send(createResponse(message));
      } else {
        return res.send(createResponse(responseMessages.errors?.failed_to_save || "Failed to save timezone"));
      }
    }

    if (name === 'convert') {
      const messageOption = data.options?.find(opt => opt.name === 'message');
      if (!messageOption) {
        return res.send(createResponse("Please provide a message containing times"));
      }
      
      const messageContent = messageOption.value;
      const timezoneOption = data.options?.find(opt => opt.name === 'timezone');
      const targetTz = timezoneOption?.value || getUserTimezone(userId);
      
      if (!targetTz) {
        return res.send(createResponse(responseMessages.errors?.no_timezone_set || "No timezone set. Use `/timezone EST` to set one"));
      }
      
      if (timezoneOption && !normalizeTimezone(timezoneOption.value)) {
        return res.send(createResponse(responseMessages.errors?.invalid_timezone || "*Invalid timezone. Use format: /convert 3:00PM EST*"));
      }
      
      const conversions = convertTimes(messageContent, targetTz);
      
      // If no timezone specified, try assuming UTC
      if (conversions.length === 0) {
        const foundTimes = extractTimes(messageContent);
        for (const timeStr of foundTimes) {
          const parsed = parseTime(timeStr, 'UTC');
          if (parsed) {
            const converted = parsed.moment.clone().tz(targetTz);
            const isSameDay = parsed.moment.format('YYYY-MM-DD') === converted.format('YYYY-MM-DD');
            
            // Format consistently with proper timezone abbreviations
            const originalFormatted = `${timeStr} UTC`;
            const convertedFormatted = `${converted.format('h:mmA')} ${getTimezoneDisplayName(targetTz)}`;
            
            conversions.push({
              original: originalFormatted,
              converted: convertedFormatted,
              date: converted.format('dddd, MMMM Do'),
              isSameDay
            });
          }
        }
      }
      
      if (conversions.length === 0) {
        return res.send(createResponse(responseMessages.errors?.no_times_found || "*No times found. Use format: /convert 3:00PM EST*"));
      }
      
      let response = (responseMessages.success?.conversion_header || "**Times in your timezone ({timezone})**\n\n").replace('{timezone}', targetTz);
      
      for (const conv of conversions) {
        const template = conv.isSameDay 
          ? (responseMessages.success?.conversion_line || "**{original}** → **{converted}**")
          : (responseMessages.success?.conversion_line_with_date || "**{original}** → **{converted}** ({date})");
        
        const line = template
          .replace('{original}', conv.original)
          .replace('{converted}', conv.converted)
          .replace('{date}', conv.date);
        response += `${line}\n`;
      }
      
      return res.send(createResponse(response.trim()));
    }

    if (name === 'mytimezone') {
      const userTimezone = getUserTimezone(userId);
      
      if (!userTimezone) {
        return res.send(createResponse(responseMessages.errors?.no_timezone_set || "No timezone set. Use `/timezone EST` to set one"));
      }
      
      try {
        const tz = moment.tz(userTimezone);
        const currentTime = tz.format('h:mm A z');
        const dateStr = tz.format('dddd, MMMM Do, YYYY');
        
        const response = (responseMessages.success?.mytimezone_display || "**Your timezone:** `{timezone}`\n**Current time:** {time}\n**Date:** {date}")
          .replace('{timezone}', userTimezone)
          .replace('{time}', currentTime)
          .replace('{date}', dateStr);
        return res.send(createResponse(response));
      } catch {
        const response = (responseMessages.success?.mytimezone_simple || "**Your timezone:** `{timezone}`").replace('{timezone}', userTimezone);
        return res.send(createResponse(response));
      }
    }

    if (name === 'help') {
      const helpText = responseMessages.help?.content || `**Commands:**
/timezone <timezone> - Set your timezone
/convert <time> - Convert a time
/mytimezone - Show your timezone
/help - Show this help

**Formats:**
• 3:00PM EST - 12-hour with timezone
• 4:30 PM PST - 12-hour with minutes  
• 16:30 GMT - 24-hour format
• 14:00 UTC - 24-hour format

**Timezones:**
• EST, PST, GMT, UTC, SGT, etc.
• America/New_York, Europe/London, Asia/Singapore
• UTC-5, UTC+3

**Auto-detection:**
I detect times in messages and convert them automatically.`;
      
      return res.send(createResponse(helpText));
    }

    return res.status(400).json({ error: 'unknown command' });
  }

  return res.status(400).json({ error: 'unknown interaction type' });
});

app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy', 
    timestamp: new Date().toISOString(),
    uptime: process.uptime()
  });
});

// Initialize
initUserPrefs();
const gateway = new GatewayClient();

// Start server
app.listen(PORT, () => {
  console.log(`Bot listening on port ${PORT}`);
  console.log('Commands: /timezone EST, /convert "Meeting at 3 PM EST"');
  console.log('React with ⏰ to messages with times for conversion');
  gateway.connect();
});

// Graceful shutdown
const shutdown = () => {
  console.log('Shutting down...');
  gateway.disconnect();
  process.exit(0);
};

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
