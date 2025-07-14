import 'dotenv/config';

// Register Discord slash commands
async function registerCommands() {
  const commands = [
    {
      name: 'timezone',
      description: 'Set your personal timezone',
      options: [{
        type: 3,
        name: 'timezone',
        description: 'Your timezone (e.g., EST, America/New_York, UTC-5)',
        required: true
      }],
      type: 1,
      integration_types: [0, 1],
      contexts: [0, 1, 2],
    },
    {
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
          description: 'Target timezone (optional)',
          required: false
        }
      ],
      type: 1,
      integration_types: [0, 1],
      contexts: [0, 1, 2],
    },
    {
      name: 'mytimezone',
      description: 'Show your current timezone setting and current time',
      type: 1,
      integration_types: [0, 1],
      contexts: [0, 1, 2],
    },
    {
      name: 'help',
      description: 'Show help information and available commands',
      type: 1,
      integration_types: [0, 1],
      contexts: [0, 1, 2],
    }
  ];

  const endpoint = `https://discord.com/api/v10/applications/${process.env.APP_ID}/commands`;

  try {
    const response = await fetch(endpoint, {
      method: 'PUT',
      body: JSON.stringify(commands),
      headers: {
        'Authorization': `Bot ${process.env.DISCORD_TOKEN}`,
        'Content-Type': 'application/json; charset=UTF-8',
      },
    });

    if (response.ok) {
      const data = await response.json();
      console.log(`Successfully registered ${data.length} commands:`);
      data.forEach(cmd => console.log(`  /${cmd.name} - ${cmd.description}`));
    } else {
      console.error('Failed to register commands');
      console.error(await response.text());
    }
  } catch (error) {
    console.error('Error registering commands:', error);
  }
}

registerCommands();
