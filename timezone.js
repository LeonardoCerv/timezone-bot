import moment from 'moment-timezone';
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { join } from 'path';

// Simple JSON file to store user timezone preferences
const DB_PATH = join(process.cwd(), 'timezones.json');

function initDB() {
  if (!existsSync(DB_PATH)) {
    writeFileSync(DB_PATH, JSON.stringify({ users: {} }, null, 2));
  }
}

function readDB() {
  try {
    if (!existsSync(DB_PATH)) {
      initDB();
    }
    const data = readFileSync(DB_PATH, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.error('Error reading database:', error);
    return { users: {} };
  }
}

function writeDB(data) {
  try {
    writeFileSync(DB_PATH, JSON.stringify(data, null, 2));
    return true;
  } catch (error) {
    console.error('Error writing database:', error);
    return false;
  }
}

initDB();

// This makes it easier for users to type "EST" instead of "America/New_York"
const timezoneAliases = {
  'EST': 'America/New_York',
  'EDT': 'America/New_York',
  'CST': 'America/Chicago', 
  'CDT': 'America/Chicago',
  'MST': 'America/Denver',
  'MDT': 'America/Denver',
  'PST': 'America/Los_Angeles',
  'PDT': 'America/Los_Angeles',
  'GMT': 'Europe/London',
  'UTC': 'UTC',
  'CET': 'Europe/Paris',
  'JST': 'Asia/Tokyo',
  'IST': 'Asia/Kolkata',
  'AEST': 'Australia/Sydney',
  'AEDT': 'Australia/Sydney'
};

/**
 * Convert user input to a valid timezone
 * Handles abbreviations like "EST", full names like "America/New_York", and offsets like "UTC-5"
 */
export function normalizeTimezone(input) {
  if (!input) return null;
  
  // First check if it's a common abbreviation we recognize
  const alias = timezoneAliases[input.toUpperCase()];
  if (alias) return alias;
  
  if (moment.tz.zone(input)) return input;
  
  // Handle UTC offset formats: UTC-5
  const offsetMatch = input.match(/^(UTC)?([+-]\d{1,2}):?(\d{2})?$/i);
  if (offsetMatch) {
    const sign = offsetMatch[2].startsWith('+') ? '+' : '-';
    const hours = Math.abs(parseInt(offsetMatch[2]));
    const minutes = offsetMatch[3] ? parseInt(offsetMatch[3]) : 0;
    
    // Validate reasonable offset ranges
    if (hours <= 14 && minutes <= 59) {
      // Note: Etc/GMT offsets are inverted (GMT+5 = UTC-5)
      return `Etc/GMT${sign === '+' ? '-' : '+'}${hours}`;
    }
  }
  
  return null;
}

/**
 * Save a user's timezone preference to our local database
 */
export function setUserTimezone(userId, timezone) {
  const normalizedTz = normalizeTimezone(timezone);
  if (!normalizedTz) return false;
  
  try {
    const data = readDB();
    data.users[userId] = {
      timezone: normalizedTz,
      displayName: timezone,
      lastUpdated: new Date().toISOString()
    };
    return writeDB(data);
  } catch (error) {
    console.error('Error saving timezone:', error);
    return false;
  }
}

/**
 * Get a user's saved timezone preference
 */
export function getUserTimezone(userId) {
  try {
    const data = readDB();
    return data.users?.[userId]?.timezone || null;
  } catch (error) {
    return null;
  }
}

/**
 * Parse a time string and figure out what timezone it's in
 * For example: "3:00 PM EST" will detect both the time and the EST timezone
 */
export function parseTimeInput(timeStr, contextTimezone = 'UTC') {
  if (!timeStr) return { moment: null, timezone: null };
  
  let parsedMoment = null;
  let detectedTimezone = contextTimezone;
  
  // Look for timezone abbreviations in the string (like "EST", "PST", "UTC-5")
  const tzMatch = timeStr.match(/\b([A-Z]{3,4}|UTC[+-]\d{1,2}:?\d{0,2})\b/i);
  if (tzMatch) {
    const tzStr = tzMatch[1];
    const normalizedTz = normalizeTimezone(tzStr);
    if (normalizedTz) {
      detectedTimezone = normalizedTz;
    }
  }
  
  // List of time formats we can recognize
  const timeFormats = [
    'h:mm A',    // 3:30 PM
    'h A',       // 3 PM  
    'HH:mm',     // 15:30
    'H:mm',      // 9:30
    'h:mm:ss A', // 3:30:00 PM
    'HH:mm:ss'   // 15:30:00
  ];
  
  // Clean up the string - remove context words and timezone info
  let cleanTimeStr = timeStr
    .replace(/\b(at|around|by|before|after)\s+/gi, '') // Remove "at 3pm" -> "3pm"
    .replace(/\b([A-Z]{3,4}|UTC[+-]\d{1,2}:?\d{0,2})\b/gi, '') // Remove timezone
    .trim();
  
  // Try each format until one works
  for (const format of timeFormats) {
    const testMoment = moment.tz(cleanTimeStr, format, detectedTimezone);
    if (testMoment.isValid()) {
      parsedMoment = testMoment;
      break;
    }
  }
  
  // Last resort: let moment.js try to parse it however it can
  if (!parsedMoment || !parsedMoment.isValid()) {
    parsedMoment = moment.tz(cleanTimeStr, detectedTimezone);
  }
  
  return {
    moment: parsedMoment && parsedMoment.isValid() ? parsedMoment : null,
    timezone: detectedTimezone
  };
}

/**
 * Find all time-like patterns in a message
 * Returns an array of strings that look like times: ["3:00 PM", "15:30", "2 PM EST"]
 */
export function extractTimesFromMessage(content) {
  
  // Regex patterns to match different time formats
  const timePatterns = [
    // Times with timezones: "3:00 PM EST", "2 PM PST"
    /\b(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)\s*([A-Z]{3,4}|UTC[+-]\d{1,2}:?\d{0,2})\b/gi,
    /\b(\d{1,2})\s*(AM|PM|am|pm)\s*([A-Z]{3,4}|UTC[+-]\d{1,2}:?\d{0,2})\b/gi,
    
    // 12-hour format: "3:00 PM", "3 PM"
    /\b(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)\b/gi,
    /\b(\d{1,2})\s*(AM|PM|am|pm)\b/gi,
    
    // 24-hour format: "15:30", "09:00"
    /\b([01]?\d|2[0-3]):([0-5]\d)\b/g,
    
    // Context words: "at 3pm", "around 15:30"
    /\b(at|around|by|before|after)\s+(\d{1,2}):?(\d{2})?\s*(AM|PM|am|pm)?\b/gi,
  ];
  
  const foundTimes = [];
  const processedSpans = []; // Keep track of what we've already found to avoid duplicates
  
  // Check each pattern against the message
  timePatterns.forEach(pattern => {
    let match;
    while ((match = pattern.exec(content)) !== null) {
      const matchText = match[0].trim();
      const matchStart = match.index;
      const matchEnd = match.index + match[0].length;
      
      // Skip if this overlaps with something we already found
      const overlaps = processedSpans.some(span => 
        (matchStart >= span.start && matchStart < span.end) ||
        (matchEnd > span.start && matchEnd <= span.end) ||
        (matchStart <= span.start && matchEnd >= span.end)
      );
      
      if (!overlaps) {
        foundTimes.push(matchText);
        processedSpans.push({ start: matchStart, end: matchEnd });
      }
    }
  });
  
  // Clean up results - remove obviously invalid matches
  return foundTimes
    .filter(time => time.length >= 2 && !/^\d{1,2}$/.test(time.trim())) // Remove single digits
    .sort((a, b) => content.indexOf(a) - content.indexOf(b)); // Sort by position in message
}

/**
 * Take a message and extract + parse all the times in it
 * Returns an array of objects with the original text and parsed time data
 */
export function parseTimesFromMessage(content, userTimezone = 'UTC') {
  const extractedTimes = extractTimesFromMessage(content);
  const parsedTimes = [];
  
  // Try to parse each found time string
  for (const timeStr of extractedTimes) {
    const parsed = parseTimeInput(timeStr, userTimezone);
    if (parsed.moment && parsed.moment.isValid()) {
      parsedTimes.push({
        original: timeStr,
        parsed: parsed
      });
    }
  }
  
  return parsedTimes;
}

/**
 * Convert a time to a user's personal timezone
 * Returns an object with formatting info for display
 */
export function convertToUserTimezone(timeData, userTimezone) {
  const userTz = normalizeTimezone(userTimezone);
  if (!userTz) return null;
  
  const converted = timeData.moment.clone().tz(userTz);
  const sourceFormat = timeData.moment.format('h:mm A z');
  const targetFormat = converted.format('h:mm A z');
  const date = converted.format('dddd, MMMM Do');
  
  return {
    original: sourceFormat,
    converted: targetFormat,
    date: date,
    timezone: userTz,
    isSameDay: timeData.moment.format('YYYY-MM-DD') === converted.format('YYYY-MM-DD')
  };
}

/**
 * Format a timezone conversion for display in Discord
 * Only shows date if the converted time is on a different day
 */
export function formatPersonalConversion(originalTime, conversion) {
  if (!conversion) {
    return `**${originalTime}** - Could not convert`;
  }
  
  let result = `**${originalTime}** → **${conversion.converted}**`;
  
  if (!conversion.isSameDay) {
    result += ` (${conversion.date})`;
  }
  
  return result;
}


