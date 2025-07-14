import os
import json
import requests
from flask import Flask, request, redirect, render_template_string
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# OAuth endpoints for Slack
SLACK_CLIENT_ID = os.environ.get("SLACK_CLIENT_ID")
SLACK_CLIENT_SECRET = os.environ.get("SLACK_CLIENT_SECRET")
SLACK_REDIRECT_URI = os.environ.get("SLACK_REDIRECT_URI", "http://localhost:3000/oauth")

# Template for success page
SUCCESS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Installation Successful - Timezone Bot</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 500px;
            margin: 20px;
        }
        .success-icon {
            font-size: 4rem;
            margin-bottom: 20px;
        }
        h1 {
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 2rem;
        }
        p {
            color: #5a6c7d;
            line-height: 1.6;
            margin-bottom: 15px;
        }
        .feature-list {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            text-align: left;
        }
        .feature-list h3 {
            color: #2c3e50;
            margin-top: 0;
            margin-bottom: 15px;
        }
        .feature-list ul {
            margin: 0;
            padding-left: 20px;
        }
        .feature-list li {
            margin-bottom: 8px;
            color: #5a6c7d;
        }
        .back-to-slack {
            display: inline-block;
            background: #4a90e2;
            color: white;
            text-decoration: none;
            padding: 12px 24px;
            border-radius: 6px;
            margin-top: 20px;
            transition: background 0.3s;
        }
        .back-to-slack:hover {
            background: #357abd;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="success-icon">🎉</div>
        <h1>Installation Successful!</h1>
        <p>Your Timezone Bot has been successfully installed to your Slack workspace.</p>
        
        <div class="feature-list">
            <h3>What you can do now:</h3>
            <ul>
                <li>Set your timezone with: <code>/timezone set EST</code></li>
                <li>Convert times automatically when mentioned in messages</li>
                <li>Get timezone help with: <code>/timezone help</code></li>
                <li>View your current timezone with: <code>/timezone show</code></li>
            </ul>
        </div>
        
        <p>The bot will automatically detect and convert times mentioned in your messages to your preferred timezone.</p>
        
        <a href="slack://open" class="back-to-slack">Back to Slack</a>
    </div>
</body>
</html>
"""

# Template for error page
ERROR_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Installation Error - Timezone Bot</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 500px;
            margin: 20px;
        }
        .error-icon {
            font-size: 4rem;
            margin-bottom: 20px;
        }
        h1 {
            color: #e74c3c;
            margin-bottom: 20px;
            font-size: 2rem;
        }
        p {
            color: #5a6c7d;
            line-height: 1.6;
            margin-bottom: 15px;
        }
        .try-again {
            display: inline-block;
            background: #e74c3c;
            color: white;
            text-decoration: none;
            padding: 12px 24px;
            border-radius: 6px;
            margin-top: 20px;
            transition: background 0.3s;
        }
        .try-again:hover {
            background: #c0392b;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="error-icon">❌</div>
        <h1>Installation Failed</h1>
        <p>Something went wrong during the installation process.</p>
        <p>Please try installing the app again, or contact support if the problem persists.</p>
        
        <a href="/install" class="try-again">Try Again</a>
    </div>
</body>
</html>
"""

# Template for install page
INSTALL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Install Timezone Bot</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            background: white;
            border-radius: 12px;
            padding: 40px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 600px;
            margin: 20px;
        }
        .bot-icon {
            font-size: 4rem;
            margin-bottom: 20px;
        }
        h1 {
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 2.5rem;
        }
        .description {
            color: #5a6c7d;
            line-height: 1.6;
            margin-bottom: 30px;
            font-size: 1.1rem;
        }
        .features {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 30px;
            margin: 30px 0;
            text-align: left;
        }
        .features h3 {
            color: #2c3e50;
            margin-top: 0;
            margin-bottom: 20px;
            text-align: center;
        }
        .features ul {
            margin: 0;
            padding-left: 20px;
        }
        .features li {
            margin-bottom: 12px;
            color: #5a6c7d;
            font-size: 1rem;
        }
        .install-button {
            display: inline-block;
            background: #4a90e2;
            color: white;
            text-decoration: none;
            padding: 15px 30px;
            border-radius: 8px;
            font-size: 1.1rem;
            font-weight: 600;
            margin-top: 20px;
            transition: all 0.3s;
            box-shadow: 0 4px 15px rgba(74, 144, 226, 0.3);
        }
        .install-button:hover {
            background: #357abd;
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(74, 144, 226, 0.4);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="bot-icon">🌍</div>
        <h1>Timezone Bot</h1>
        <p class="description">Automatically convert times to your preferred timezone in Slack conversations.</p>
        
        <div class="features">
            <h3>✨ Features</h3>
            <ul>
                <li><strong>Automatic Time Conversion:</strong> Detects times in messages and shows them in your timezone</li>
                <li><strong>Personal Timezone Settings:</strong> Set your preferred timezone once and forget about it</li>
                <li><strong>Multiple Format Support:</strong> Works with 12-hour, 24-hour, and timezone-specific formats</li>
                <li><strong>Easy Commands:</strong> Simple slash commands to manage your timezone preferences</li>
                <li><strong>Cross-Platform:</strong> Works seamlessly across all Slack clients</li>
            </ul>
        </div>
        
        <p>Ready to never miss a meeting due to timezone confusion again?</p>
        
        <a href="https://slack.com/oauth/v2/authorize?client_id={{ client_id }}&scope=chat:write,commands&user_scope=&redirect_uri={{ redirect_uri }}" class="install-button">
            Add to Slack
        </a>
    </div>
</body>
</html>
"""

def save_team_token(team_id, access_token, bot_user_id):
    """Save the team's access token to a JSON file"""
    tokens_file = 'team_tokens.json'
    
    # Load existing tokens
    tokens = {}
    if os.path.exists(tokens_file):
        try:
            with open(tokens_file, 'r') as f:
                tokens = json.load(f)
        except json.JSONDecodeError:
            tokens = {}
    
    # Save new token
    tokens[team_id] = {
        'access_token': access_token,
        'bot_user_id': bot_user_id,
        'installed_at': json.dumps(os.times(), default=str)
    }
    
    # Write back to file
    with open(tokens_file, 'w') as f:
        json.dump(tokens, f, indent=2)

@app.route('/install')
def install():
    """Show the installation page with Add to Slack button"""
    return render_template_string(
        INSTALL_TEMPLATE,
        client_id=SLACK_CLIENT_ID,
        redirect_uri=SLACK_REDIRECT_URI
    )

@app.route('/oauth')
def oauth_callback():
    """Handle the OAuth callback from Slack"""
    try:
        # Get the authorization code from Slack
        code = request.args.get('code')
        error = request.args.get('error')
        
        if error:
            print(f"OAuth error: {error}")
            return redirect('/error')
        
        if not code:
            print("No authorization code received")
            return redirect('/error')
        
        # Exchange the code for an access token
        token_response = requests.post('https://slack.com/api/oauth.v2.access', data={
            'client_id': SLACK_CLIENT_ID,
            'client_secret': SLACK_CLIENT_SECRET,
            'code': code,
            'redirect_uri': SLACK_REDIRECT_URI
        })
        
        token_data = token_response.json()
        
        if not token_data.get('ok'):
            print(f"Token exchange failed: {token_data}")
            return redirect('/error')
        
        # Extract important information
        team_id = token_data.get('team', {}).get('id')
        access_token = token_data.get('access_token')
        bot_user_id = token_data.get('bot_user_id')
        
        if not all([team_id, access_token, bot_user_id]):
            print("Missing required OAuth data")
            return redirect('/error')
        
        # Save the team's token
        save_team_token(team_id, access_token, bot_user_id)
        
        print(f"Successfully installed for team {team_id}")
        
        # Redirect to success page
        return redirect('/thanks')
        
    except Exception as e:
        print(f"OAuth callback error: {e}")
        return redirect('/error')

@app.route('/thanks')
def thanks():
    """Show success page after successful installation"""
    return render_template_string(SUCCESS_TEMPLATE)

@app.route('/error')
def error():
    """Show error page if installation fails"""
    return render_template_string(ERROR_TEMPLATE)

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'ok', 'service': 'timezone-bot-oauth'}

if __name__ == '__main__':
    # Check required environment variables
    if not SLACK_CLIENT_ID or not SLACK_CLIENT_SECRET:
        print("Error: SLACK_CLIENT_ID and SLACK_CLIENT_SECRET must be set in environment variables")
        exit(1)
    
    print("Starting OAuth server...")
    print(f"Install URL: http://localhost:3000/install")
    print(f"OAuth Redirect URI: {SLACK_REDIRECT_URI}")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=3000, debug=True)
