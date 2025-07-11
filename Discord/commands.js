import 'dotenv/config';
import { InstallGlobalCommands } from './utils.js';

// Set users personal timezone
const TIMEZONE_COMMAND = {
  name: 'timezone',
  description: 'Set your personal timezone',
  options: [
    {
      type: 3,
      name: 'timezone',
      description: 'Your timezone (e.g., EST, America/New_York, UTC-5)',
      required: true
    }
  ],
  type: 1,
  integration_types: [0, 1],
  contexts: [0, 1, 2],
};

// Converting times in messages
const TIME_COMMAND = {
  name: 'time',
  description: 'Convert times in a message to your timezone or specified timezone',
  options: [
    {
      type: 3,
      name: 'message',
      description: 'Message containing times to convert',
      required: true
    },
    {
      type: 3,
      name: 'timezone',
      description: 'Target timezone (optional - uses your personal timezone if not provided)',
      required: false
    }
  ],
  type: 1,
  integration_types: [0, 1],
  contexts: [0, 1, 2],
};

const ALL_COMMANDS = [TIMEZONE_COMMAND, TIME_COMMAND];
InstallGlobalCommands(process.env.APP_ID, ALL_COMMANDS);