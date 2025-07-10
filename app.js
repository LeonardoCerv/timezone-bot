import 'dotenv/config';
import express from 'express';
import {
  InteractionResponseFlags,
  InteractionResponseType,
  InteractionType,
  verifyKeyMiddleware,
} from 'discord-interactions';
import { 
  setUserTimezone, 
  getUserTimezone, 
  parseTimesFromMessage, 
  convertToUserTimezone,
  formatPersonalConversion,
  normalizeTimezone,
  extractTimesFromMessage
} from './timezone.js';

const app = express();
const PORT = process.env.PORT || 3000;
app.use(express.json());

/**
 * Main function works for both user and specific timezones
 * If targetTimezone is null, uses the user's personal timezone
 * If targetTimezone is provided, converts to that specific timezone
 */
function handleTimeConversion(userId, messageContent, targetTimezone = null) {

  const timezone = targetTimezone || getUserTimezone(userId);
  
  // check if there is a timezone
  if (!timezone) {
    return createResponse("❌ Please set your timezone first using `/timezone EST` (or your timezone)");
  }

  // validate the custom timezone
  if (targetTimezone && !normalizeTimezone(targetTimezone)) {
    return createResponse(`❌ Invalid timezone: ${targetTimezone}. Use formats like EST, America/New_York, UTC-5`);
  }

  // Find times in the message
  const extractedTimes = extractTimesFromMessage(messageContent);
  if (extractedTimes.length === 0) {
    return createResponse("❌ No times found in the message. I can detect formats like: 3:00 PM, 15:00, 3 PM EST");
  }
  
  // parse times into time objects
  const parsedTimes = parseTimesFromMessage(messageContent, 'UTC');
  if (parsedTimes.length === 0) {
    return createResponse(`❌ Found times (${extractedTimes.join(', ')}) but couldn't parse them`);
  }
  
  // Convert times to the selected timezone
  const isPersonalConversion = !targetTimezone;
  const title = isPersonalConversion ? `Times in your timezone (${timezone})` : `Times converted to ${targetTimezone}`;
  let responseContent = `**${title}**\n\n`;
  
  for (const timeData of parsedTimes) {
    if (isPersonalConversion) {

      // Conversion for personal timezone
      const conversion = convertToUserTimezone(timeData.parsed, timezone);
      const formatted = formatPersonalConversion(timeData.original, conversion);
      responseContent += `${formatted}\n`;
    } 
    else {

      // Conversion for custom timezone
      const normalizedTz = normalizeTimezone(targetTimezone);
      const converted = timeData.parsed.moment.clone().tz(normalizedTz);
      const targetFormat = converted.format('h:mm A z');
      const isSameDay = timeData.parsed.moment.format('YYYY-MM-DD') === converted.format('YYYY-MM-DD');
      
      let result = `**${timeData.original}** → **${targetFormat}**`;
      if (!isSameDay) {
        result += ` (${converted.format('dddd, MMMM Do')})`;
      }
      responseContent += `${result}\n`;
    }
  }
  
  return createResponse(responseContent.trim());
}

/**
 * Helper func to create responses
 */
function createResponse(message) {
  return {
    type: InteractionResponseType.CHANNEL_MESSAGE_WITH_SOURCE,
    data: {
      flags: InteractionResponseFlags.EPHEMERAL,
      content: message
    }
  };
}

// Discord webhook endpoint
app.post('/interactions', verifyKeyMiddleware(process.env.PUBLIC_KEY), async function (req, res) {
  const { type, data } = req.body;

  // Respond to Discord's ping
  if (type === InteractionType.PING) {
    return res.send({ type: InteractionResponseType.PONG });
  }

  // Handle slash commands
  if (type === InteractionType.APPLICATION_COMMAND) {
    const { name } = data;
    const { user, member } = req.body;

    // Get user ID
    const userId = req.body.context === 0 ? member.user.id : user.id;

    // handle TIMEZONE SET
    if (name === 'timezone') {
      const timezoneInput = data.options[0].value;
      
      if (!normalizeTimezone(timezoneInput)) {
        return res.send(createResponse("❌ Invalid timezone. Use formats like: EST, America/New_York, UTC-5"));
      }
      
      const success = setUserTimezone(userId, timezoneInput);
      const message = success 
        ? `✅ Timezone set to **${timezoneInput}**. Now use \`/time\` to convert times!`
        : "Failed to save timezone. Please try again.";
        
      return res.send(createResponse(message));
    }

    // Handle TIME CONVERSION
    if (name === 'time') {
      // Get required message parameter
      const messageOption = data.options?.find(opt => opt.name === 'message');
      if (!messageOption) {
        return res.send(createResponse("❌ Please provide a message containing times to convert"));
      }
      
      const messageContent = messageOption.value;
      const timezoneOption = data.options?.find(opt => opt.name === 'timezone');
      const targetTimezone = timezoneOption?.value || null;
      
      const response = handleTimeConversion(userId, messageContent, targetTimezone);
      return res.send(response);
    }

    return res.status(400).json({ error: 'unknown command' });
  }

  return res.status(400).json({ error: 'unknown interaction type' });
});

// Start the server
app.listen(PORT, () => {
  console.log(`Bot listening on port ${PORT}`);
  console.log('Available commands:');
  console.log('  /timezone EST - Set your timezone');
  console.log('  /time "Meeting at 3 PM EST" - Convert to your timezone');
  console.log('  /time "Call at 2 PM GMT" "PST" - Convert to specific timezone');
});
