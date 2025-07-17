import os
import json
import hashlib
import hmac
from flask import Flask, request, render_template_string, redirect, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Get bot token from environment
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
BOT_USERNAME = "Timezone123Bot"
DOMAIN = os.environ.get("DOMAIN", "telegrambot.leonardocerv.hackclub.app")

# Template for installation page
INSTALL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>install timezone bot</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
            margin: 0;
            padding: 0;
            background: #f8f8f8;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: #fff;
            border: 1px solid #e5e5e5;
            padding: 3rem 2rem;
            max-width: 600px;
            margin: 2rem;
        }
        h1 {
            color: #1a1a1a;
            margin-bottom: 1rem;
            font-size: 2rem;
            font-weight: 400;
            letter-spacing: -0.025em;
        }
        .description {
            color: #666;
            line-height: 1.5;
            margin-bottom: 2rem;
            font-size: 0.875rem;
        }
        .features {
            background: #1a1a1a;
            color: #e5e5e5;
            padding: 1.5rem;
            margin: 2rem 0;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace;
        }
        .features h3 {
            color: #e5e5e5;
            margin-top: 0;
            margin-bottom: 1rem;
            font-weight: 500;
            font-size: 1rem;
        }
        .features ul {
            margin: 0;
            padding-left: 1rem;
            list-style: none;
        }
        .features li {
            margin-bottom: 0.75rem;
            color: #e5e5e5;
            font-size: 0.875rem;
            line-height: 1.4;
        }
        .auth-section {
            margin: 2rem 0;
            padding: 1.5rem;
            background: #f8f8f8;
            border: 1px solid #e5e5e5;
            text-align: center;
        }
        .auth-section h3 {
            color: #1a1a1a;
            margin-top: 0;
            margin-bottom: 1rem;
            font-weight: 500;
            font-size: 1rem;
        }
        .auth-section p {
            color: #666;
            margin-bottom: 1.5rem;
            font-size: 0.875rem;
        }
        .telegram-widget {
            display: flex;
            justify-content: center;
            margin: 1rem 0;
        }
        .success-message {
            display: none;
            background: #e8f5e8;
            border: 1px solid #c3e6c3;
            padding: 1rem;
            margin: 1rem 0;
            color: #2d5a2d;
            font-size: 0.875rem;
        }
        .error-message {
            display: none;
            background: #fee;
            border: 1px solid #fcc;
            padding: 1rem;
            margin: 1rem 0;
            color: #c33;
            font-size: 0.875rem;
        }
        .instructions {
            background: #1a1a1a;
            color: #e5e5e5;
            padding: 1.5rem;
            margin: 2rem 0;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace;
        }
        .instructions h3 {
            color: #e5e5e5;
            margin-top: 0;
            margin-bottom: 1rem;
            font-weight: 500;
            font-size: 1rem;
        }
        .instructions ol {
            margin: 0;
            padding-left: 1.5rem;
        }
        .instructions li {
            margin-bottom: 0.75rem;
            color: #e5e5e5;
            font-size: 0.875rem;
            line-height: 1.4;
        }
        .instructions code {
            background: #333;
            color: #e5e5e5;
            padding: 0.2rem 0.4rem;
            font-size: 0.8rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>timezone bot</h1>
        <p class="description">automatically convert times to your preferred timezone in telegram conversations</p>
        
        <div class="features">
            <h3>features</h3>
            <ul>
                <li>automatic time conversion: detects times in messages and shows them in your timezone</li>
                <li>personal timezone settings: set your preferred timezone once and forget about it</li>
                <li>multiple format support: works with 12-hour, 24-hour, and timezone-specific formats</li>
                <li>simple commands: easy commands to manage your timezone preferences</li>
                <li>private and group chats: works in both private messages and group conversations</li>
            </ul>
        </div>

        <div class="instructions">
            <h3>installation steps</h3>
            <ol>
                <li>first, start a conversation with the bot: <code>@{{ bot_username }}</code></li>
                <li>send <code>/start</code> to activate the bot</li>
                <li>then authenticate below to link your telegram account</li>
                <li>set your timezone with <code>/timezone EST</code></li>
                <li>the bot will automatically convert times in your messages</li>
            </ol>
        </div>
        
        <div class="auth-section">
            <h3>authenticate with telegram</h3>
            <p>click the button below to link your telegram account and enable timezone conversion</p>
            
            <div class="telegram-widget">
                <script async src="https://telegram.org/js/telegram-widget.js?22" 
                        data-telegram-login="{{ bot_username }}" 
                        data-size="large" 
                        data-onauth="onTelegramAuth(user)" 
                        data-request-access="write"></script>
            </div>
            
            <div id="successMessage" class="success-message">
                <strong>success!</strong> your telegram account has been linked. you can now use the bot in telegram.
            </div>
            
            <div id="errorMessage" class="error-message">
                <strong>error:</strong> authentication failed. make sure the domain is set up with @BotFather using /setdomain command.
            </div>
        </div>
    </div>

    <script type="text/javascript">
        function onTelegramAuth(user) {
            console.log('Telegram auth received:', user);
            
            // Send auth data to server for verification
            fetch('/telegram/auth', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(user)
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('successMessage').style.display = 'block';
                    document.getElementById('errorMessage').style.display = 'none';
                } else {
                    document.getElementById('errorMessage').style.display = 'block';
                    document.getElementById('successMessage').style.display = 'none';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                document.getElementById('errorMessage').style.display = 'block';
                document.getElementById('successMessage').style.display = 'none';
            });
        }
    </script>
</body>
</html>
"""

def verify_telegram_auth(auth_data):
    """Verify the authentication data received from Telegram"""
    if not BOT_TOKEN:
        return False
    
    # Extract hash from auth_data
    received_hash = auth_data.get('hash')
    if not received_hash:
        return False
    
    # Create data check string
    check_data = []
    for key, value in sorted(auth_data.items()):
        if key != 'hash':
            check_data.append(f"{key}={value}")
    
    data_check_string = '\n'.join(check_data)
    
    # Create secret key (SHA256 hash of bot token)
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    
    # Calculate HMAC-SHA256
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return calculated_hash == received_hash

def save_user_auth(user_data):
    """Save user authentication data"""
    users_file = 'telegram_users.json'
    
    # Load existing users
    users = {}
    if os.path.exists(users_file):
        try:
            with open(users_file, 'r') as f:
                users = json.load(f)
        except json.JSONDecodeError:
            users = {}
    
    # Save user data
    user_id = str(user_data['id'])
    users[user_id] = {
        'id': user_data['id'],
        'first_name': user_data.get('first_name', ''),
        'last_name': user_data.get('last_name', ''),
        'username': user_data.get('username', ''),
        'photo_url': user_data.get('photo_url', ''),
        'auth_date': user_data.get('auth_date', ''),
        'authenticated': True
    }
    
    # Write back to file
    with open(users_file, 'w') as f:
        json.dump(users, f, indent=2)
    
    return True

@app.route('/')
def index():
    """Show the installation page or handle challenge parameter"""
    # Check if challenge parameter is provided
    challenge = request.args.get('challenge')
    if challenge:
        return challenge
    
    # Otherwise, show the installation page
    return render_template_string(INSTALL_TEMPLATE, bot_username=BOT_USERNAME)

@app.route('/install')
def install():
    """Alternative install route"""
    return redirect('/')

@app.route('/telegram/auth', methods=['POST'])
def telegram_auth():
    """Handle Telegram authentication callback"""
    try:
        auth_data = request.json
        
        if not auth_data:
            return jsonify({'success': False, 'error': 'No authentication data received'})
        
        # Verify the authentication
        if not verify_telegram_auth(auth_data):
            return jsonify({'success': False, 'error': 'Authentication verification failed'})
        
        # Save user data
        if save_user_auth(auth_data):
            return jsonify({'success': True, 'message': 'Authentication successful'})
        else:
            return jsonify({'success': False, 'error': 'Failed to save user data'})
            
    except Exception as e:
        print(f"Authentication error: {e}")
        return jsonify({'success': False, 'error': 'Server error'})

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'ok', 'service': 'timezone-bot-telegram'}

if __name__ == '__main__':
    # Check required environment variables
    if not BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN must be set in environment variables")
        exit(1)
    
    print("Starting Telegram Bot Web Server...")
    print(f"Install URL: https://{DOMAIN}/")
    print(f"Bot Username: @{BOT_USERNAME}")
    
    # Run the Flask app
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
