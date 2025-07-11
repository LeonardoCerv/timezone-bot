import 'dotenv/config';
import WebSocket from 'ws';
import { 
  getUserTimezone, 
  parseTimesFromMessage, 
  convertToUserTimezone,
  formatPersonalConversion,
  extractTimesFromMessage
} from './timezone.js';

class DiscordGatewayClient {
  constructor(token) {
    this.token = token;
    this.ws = null;
    this.heartbeatInterval = null;
    this.sessionId = null;
    this.sequenceNumber = null;
    this.isReconnecting = false;
    
    // Time-related emojis that trigger the bot
    this.timeEmojis = ['⏰', '⏳', '⏱️', '🕐', '🕑', '🕒', '🕓', '🕔', '🕕', '🕖', '🕗', '🕘', '🕙', '🕚', '🕛'];
  }

  connect() {
    this.ws = new WebSocket('wss://gateway.discord.gg/?v=10&encoding=json');
    
    this.ws.on('open', () => {
      console.log('Connected to Discord Gateway');
    });

    this.ws.on('message', (data) => {
      const message = JSON.parse(data);
      this.handleMessage(message);
    });

    this.ws.on('close', (code, reason) => {
      console.log(`Gateway connection closed: ${code} - ${reason}`);
      this.cleanup();
      
      // Attempt to reconnect if it wasn't a clean shutdown
      if (code !== 1000 && !this.isReconnecting) {
        this.reconnect();
      }
    });

    this.ws.on('error', (error) => {
      console.error('Gateway error:', error);
    });
  }

  reconnect() {
    if (this.isReconnecting) return;
    
    this.isReconnecting = true;
    console.log('Attempting to reconnect in 5 seconds...');
    
    setTimeout(() => {
      this.isReconnecting = false;
      this.connect();
    }, 5000);
  }

  cleanup() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  handleMessage(message) {
    const { op, d, s, t } = message;
    
    if (s) {
      this.sequenceNumber = s;
    }

    switch (op) {
      case 10: // Hello
        this.startHeartbeat(d.heartbeat_interval);
        this.identify();
        break;
        
      case 11: // Heartbeat ACK
        console.log('Heartbeat acknowledged');
        break;
        
      case 0: // Dispatch
        this.handleDispatch(t, d);
        break;
        
      case 1: // Heartbeat request
        this.sendHeartbeat();
        break;
        
      case 7: // Reconnect
        console.log('Gateway requested reconnect');
        this.reconnect();
        break;
        
      case 9: // Invalid session
        console.log('Invalid session, reconnecting...');
        this.sessionId = null;
        this.sequenceNumber = null;
        setTimeout(() => this.identify(), 5000);
        break;
    }
  }

  startHeartbeat(interval) {
    this.heartbeatInterval = setInterval(() => {
      this.sendHeartbeat();
    }, interval);
  }

  sendHeartbeat() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        op: 1,
        d: this.sequenceNumber
      }));
    }
  }

  identify() {
    const identifyPayload = {
      op: 2,
      d: {
        token: this.token,
        intents: 
          (1 << 0) |  // GUILDS
          (1 << 10) | // GUILD_MESSAGE_REACTIONS  
          (1 << 15) | // MESSAGE_CONTENT
          (1 << 12),  // DIRECT_MESSAGES
        properties: {
          os: process.platform,
          browser: 'discord-timezone-bot',
          device: 'discord-timezone-bot'
        }
      }
    };

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(identifyPayload));
    }
  }

  async handleDispatch(eventType, eventData) {
    switch (eventType) {
      case 'READY':
        console.log(`Bot ready! Logged in as ${eventData.user.username}#${eventData.user.discriminator}`);
        this.sessionId = eventData.session_id;
        break;
        
      case 'MESSAGE_REACTION_ADD':
        await this.handleReactionAdd(eventData);
        break;
    }
  }

  async handleReactionAdd(data) {
    const { user_id, channel_id, message_id, emoji, member } = data;
    
    // Skip bot reactions
    if (member?.user?.bot) return;
    
    // Check if it's a time-related emoji
    if (!this.timeEmojis.includes(emoji.name)) return;
    
    console.log(`Time emoji reaction detected: ${emoji.name} by user ${user_id} on message ${message_id}`);

    try {
      // Get the original message content
      const messageContent = await this.getMessageContent(channel_id, message_id);
      if (!messageContent) {
        console.error('Could not fetch message content');
        return;
      }

      // Check if user has a timezone set
      const userTimezone = getUserTimezone(user_id);
      if (!userTimezone) {
        const promptMessage = "⏰ **Set Your Timezone First!**\n\n" +
          "I noticed you reacted with a time emoji, but you haven't set your timezone yet.\n\n" +
          "Use `/timezone EST` (or your timezone) in any server where I'm available to set your timezone.\n\n" +
          "Supported formats: EST, America/New_York, UTC-5, etc.";
        
        await this.sendDirectMessage(user_id, promptMessage);
        return;
      }

      // Extract and convert times
      const extractedTimes = extractTimesFromMessage(messageContent);
      if (extractedTimes.length === 0) {
        const noTimeMessage = "⏰ **No Times Found**\n\n" +
          "I couldn't find any times in that message. I can detect formats like:\n" +
          "• 3:00 PM\n• 15:00\n• 3 PM EST\n• 2:30 PM GMT";
        
        await this.sendDirectMessage(user_id, noTimeMessage);
        return;
      }

      // Parse and convert times
      const parsedTimes = parseTimesFromMessage(messageContent, 'UTC');
      if (parsedTimes.length === 0) {
        const parseErrorMessage = `⏰ **Couldn't Parse Times**\n\n` +
          `Found times (${extractedTimes.join(', ')}) but couldn't parse them properly.`;
        
        await this.sendDirectMessage(user_id, parseErrorMessage);
        return;
      }

      // Convert times to user's timezone
      let responseContent = `⏰ **Times in your timezone (${userTimezone})**\n\n`;
      
      // Include the original message
      responseContent += `**Original message:**\n> ${messageContent}\n\n**Converted times:**\n`;
      
      for (const timeData of parsedTimes) {
        const conversion = convertToUserTimezone(timeData.parsed, userTimezone);
        const formatted = formatPersonalConversion(timeData.original, conversion);
        responseContent += `${formatted}\n`;
      }

      responseContent += `\n*Reacted to message in <#${channel_id}>*`;
      
      // Send the conversion as a DM
      await this.sendDirectMessage(user_id, responseContent.trim());
      
    } catch (error) {
      console.error('Error handling reaction:', error);
    }
  }

  async getMessageContent(channelId, messageId) {
    const url = `https://discord.com/api/v10/channels/${channelId}/messages/${messageId}`;
    
    try {
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bot ${this.token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        console.error('Failed to fetch message:', response.status, await response.text());
        return null;
      }

      const message = await response.json();
      return message.content;
    } catch (error) {
      console.error('Error fetching message:', error);
      return null;
    }
  }

  async sendDirectMessage(userId, content) {
    try {
      // First, create a DM channel with the user
      const dmResponse = await fetch('https://discord.com/api/v10/users/@me/channels', {
        method: 'POST',
        headers: {
          'Authorization': `Bot ${this.token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          recipient_id: userId
        })
      });

      if (!dmResponse.ok) {
        console.error('Failed to create DM channel:', dmResponse.status, await dmResponse.text());
        return false;
      }

      const dmChannel = await dmResponse.json();

      // Send the message to the DM channel
      const messageResponse = await fetch(`https://discord.com/api/v10/channels/${dmChannel.id}/messages`, {
        method: 'POST',
        headers: {
          'Authorization': `Bot ${this.token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          content: content
        })
      });

      if (!messageResponse.ok) {
        console.error('Failed to send DM:', messageResponse.status, await messageResponse.text());
        return false;
      }

      console.log(`Sent DM to user ${userId}`);
      return true;
    } catch (error) {
      console.error('Error sending DM:', error);
      return false;
    }
  }

  disconnect() {
    this.cleanup();
    if (this.ws) {
      this.ws.close(1000, 'Bot shutting down');
    }
  }
}

// Initialize and start the gateway client
const gatewayClient = new DiscordGatewayClient(process.env.DISCORD_TOKEN);

// Handle process termination
process.on('SIGINT', () => {
  console.log('Shutting down gateway client...');
  gatewayClient.disconnect();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('Shutting down gateway client...');
  gatewayClient.disconnect();
  process.exit(0);
});

export { gatewayClient };

// Auto-start if this file is run directly
if (import.meta.url === `file://${process.argv[1]}`) {
  console.log('Starting Discord Gateway Client...');
  gatewayClient.connect();
}