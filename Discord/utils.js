import 'dotenv/config';

// Install Discord slash commands globally
export async function InstallGlobalCommands(appId, commands) {
  const endpoint = `https://discord.com/api/v10/applications/${appId}/commands`;

  try {
    const res = await fetch(endpoint, {
      method: 'PUT',
      body: JSON.stringify(commands),
      headers: {
        'Authorization': `Bot ${process.env.DISCORD_TOKEN}`,
        'Content-Type': 'application/json; charset=UTF-8',
      },
    });

    if (res.ok) {
      console.log('✅ Successfully installed global commands');
      const data = await res.json();
      console.log(`📝 Installed ${data.length} commands:`);
      data.forEach(cmd => console.log(`   • /${cmd.name} - ${cmd.description}`));
    } else {
      console.error('❌ Failed to install global commands');
      const errorText = await res.text();
      console.error(errorText);
    }
  } catch (err) {
    console.error('❌ Error installing global commands:', err);
  }
}

// Verify Discord signature for webhook requests
export function verifyDiscordSignature(signature, body, timestamp) {
  const crypto = require('crypto');
  const publicKey = process.env.PUBLIC_KEY;
  
  const hash = crypto
    .createHmac('sha256', publicKey)
    .update(timestamp + body)
    .digest('hex');
    
  return hash === signature;
}

// Get Discord user information
export async function getDiscordUser(userId) {
  const endpoint = `https://discord.com/api/v10/users/${userId}`;
  
  try {
    const res = await fetch(endpoint, {
      headers: {
        'Authorization': `Bot ${process.env.DISCORD_TOKEN}`,
        'Content-Type': 'application/json',
      },
    });

    if (res.ok) {
      return await res.json();
    } else {
      console.error('Failed to fetch user:', res.status, await res.text());
      return null;
    }
  } catch (err) {
    console.error('Error fetching user:', err);
    return null;
  }
}

// Get Discord guild information
export async function getDiscordGuild(guildId) {
  const endpoint = `https://discord.com/api/v10/guilds/${guildId}`;
  
  try {
    const res = await fetch(endpoint, {
      headers: {
        'Authorization': `Bot ${process.env.DISCORD_TOKEN}`,
        'Content-Type': 'application/json',
      },
    });

    if (res.ok) {
      return await res.json();
    } else {
      console.error('Failed to fetch guild:', res.status, await res.text());
      return null;
    }
  } catch (err) {
    console.error('Error fetching guild:', err);
    return null;
  }
}

// Send a message to a Discord channel
export async function sendChannelMessage(channelId, content, options = {}) {
  const endpoint = `https://discord.com/api/v10/channels/${channelId}/messages`;
  
  const payload = {
    content: content,
    ...options
  };
  
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Authorization': `Bot ${process.env.DISCORD_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      return await res.json();
    } else {
      console.error('Failed to send message:', res.status, await res.text());
      return null;
    }
  } catch (err) {
    console.error('Error sending message:', err);
    return null;
  }
}

// Format user mention
export function formatUserMention(userId) {
  return `<@${userId}>`;
}

// Format channel mention
export function formatChannelMention(channelId) {
  return `<#${channelId}>`;
}

// Format timestamp for Discord
export function formatDiscordTimestamp(date, format = 'f') {
  const timestamp = Math.floor(date.getTime() / 1000);
  return `<t:${timestamp}:${format}>`;
}

// Rate limit handler for Discord API
export class RateLimiter {
  constructor() {
    this.requests = new Map();
  }

  async checkLimit(key, limit = 5, window = 60000) {
    const now = Date.now();
    const requests = this.requests.get(key) || [];
    
    // Remove old requests outside the window
    const validRequests = requests.filter(time => now - time < window);
    
    if (validRequests.length >= limit) {
      const oldestRequest = Math.min(...validRequests);
      const waitTime = window - (now - oldestRequest);
      return { allowed: false, waitTime };
    }
    
    validRequests.push(now);
    this.requests.set(key, validRequests);
    
    return { allowed: true, waitTime: 0 };
  }
}

// Validate Discord snowflake ID
export function isValidSnowflake(id) {
  return /^\d{17,19}$/.test(id);
}

// Parse Discord timestamp from snowflake
export function getTimestampFromSnowflake(snowflake) {
  const timestamp = (BigInt(snowflake) >> 22n) + 1420070400000n;
  return new Date(Number(timestamp));
}