#!/usr/bin/env node

import 'dotenv/config';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Validate environment variables
const requiredEnvVars = [
  'DISCORD_TOKEN',
  'PUBLIC_KEY',
  'APP_ID'
];

const missingVars = requiredEnvVars.filter(varName => !process.env[varName]);

if (missingVars.length > 0) {
  console.error('❌ Missing required environment variables:');
  missingVars.forEach(varName => {
    console.error(`   • ${varName}`);
  });
  console.error('\nPlease check your .env file and ensure all required variables are set.');
  process.exit(1);
}

console.log('🚀 Starting Discord Timezone Bot...');
console.log('');

// Function to start the bot
function startBot() {
  const botProcess = spawn('node', [join(__dirname, 'app.js')], {
    stdio: 'inherit',
    env: process.env
  });

  botProcess.on('error', (error) => {
    console.error('❌ Failed to start bot:', error);
    process.exit(1);
  });

  botProcess.on('exit', (code, signal) => {
    if (code !== 0) {
      console.error(`❌ Bot exited with code ${code}, signal ${signal}`);
      
      // Auto-restart on unexpected exit
      if (code !== 0 && signal !== 'SIGTERM' && signal !== 'SIGINT') {
        console.log('🔄 Restarting bot in 5 seconds...');
        setTimeout(startBot, 5000);
      }
    }
  });

  // Handle graceful shutdown
  process.on('SIGINT', () => {
    console.log('\n🛑 Shutting down bot...');
    botProcess.kill('SIGINT');
    process.exit(0);
  });

  process.on('SIGTERM', () => {
    console.log('\n🛑 Shutting down bot...');
    botProcess.kill('SIGTERM');
    process.exit(0);
  });

  return botProcess;
}

// Check if commands need to be registered
const shouldRegisterCommands = process.argv.includes('--register-commands');

if (shouldRegisterCommands) {
  console.log('📝 Registering Discord commands...');
  
  const registerProcess = spawn('node', [join(__dirname, 'commands.js')], {
    stdio: 'inherit',
    env: process.env
  });

  registerProcess.on('exit', (code) => {
    if (code === 0) {
      console.log('✅ Commands registered successfully');
      console.log('');
      startBot();
    } else {
      console.error('❌ Failed to register commands');
      process.exit(1);
    }
  });
} else {
  startBot();
}

// Display helpful information
console.log('ℹ️  Bot Information:');
console.log(`   • Environment: ${process.env.NODE_ENV || 'production'}`);
console.log(`   • Port: ${process.env.PORT || 3000}`);
console.log(`   • App ID: ${process.env.APP_ID}`);
console.log('');
console.log('📚 Usage:');
console.log('   • To register commands: node start.js --register-commands');
console.log('   • To start normally: node start.js');
console.log('   • To stop: Ctrl+C');
console.log('');