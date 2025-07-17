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
SLACK_REDIRECT_URI = os.environ.get("SLACK_REDIRECT_URI", "http://localhost:8944/oauth")

# Template for success page
SUCCESS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>installation successful</title>
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
            max-width: 500px;
            margin: 2rem;
        }
        h1 {
            color: #1a1a1a;
            margin-bottom: 1rem;
            font-size: 1.5rem;
            font-weight: 500;
            letter-spacing: -0.015em;
        }
        p {
            color: #666;
            line-height: 1.5;
            margin-bottom: 1rem;
            font-size: 0.875rem;
        }
        .commands {
            background: #1a1a1a;
            color: #e5e5e5;
            padding: 1.5rem;
            margin: 1.5rem 0;
            font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace;
        }
        .commands h3 {
            color: #e5e5e5;
            margin-top: 0;
            margin-bottom: 1rem;
            font-weight: 500;
            font-size: 1rem;
        }
        .commands ul {
            margin: 0;
            padding-left: 1rem;
            list-style: none;
        }
        .commands li {
            margin-bottom: 0.5rem;
            color: #e5e5e5;
            font-size: 0.875rem;
        }
        .commands code {
            background: none;
            color: #e5e5e5;
            padding: 0;
        }
        .back-link {
            display: inline-block;
            color: #1a1a1a;
            text-decoration: none;
            font-size: 0.875rem;
            border-bottom: 1px solid #1a1a1a;
            padding-bottom: 1px;
            margin-top: 1rem;
        }
        .back-link:hover {
            opacity: 0.7;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>installation successful</h1>
        <p>timezone bot has been added to your slack workspace.</p>
        
        <div class="commands">
            <h3>available commands:</h3>
            <ul>
                <li>/timezone set EST</li>
                <li>/timezone show</li>
                <li>/timezone help</li>
            </ul>
        </div>
        
        <p>the bot will automatically detect and convert times mentioned in messages to your preferred timezone.</p>
        
        <a href="slack://open" class="back-link">back to slack →</a>
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
    <title>installation error</title>
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
            max-width: 500px;
            margin: 2rem;
        }
        h1 {
            color: #1a1a1a;
            margin-bottom: 1rem;
            font-size: 1.5rem;
            font-weight: 500;
            letter-spacing: -0.015em;
        }
        p {
            color: #666;
            line-height: 1.5;
            margin-bottom: 1rem;
            font-size: 0.875rem;
        }
        .try-again {
            display: inline-block;
            color: #1a1a1a;
            text-decoration: none;
            font-size: 0.875rem;
            border-bottom: 1px solid #1a1a1a;
            padding-bottom: 1px;
            margin-top: 1rem;
        }
        .try-again:hover {
            opacity: 0.7;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>installation failed</h1>
        <p>something went wrong during the installation process.</p>
        <p>please try installing the app again, or contact support if the problem persists.</p>
        
        <a href="/install" class="try-again">try again →</a>
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
        .install-button {
            display: inline-block;
            color: #1a1a1a;
            text-decoration: none;
            font-size: 0.875rem;
            border-bottom: 1px solid #1a1a1a;
            padding-bottom: 1px;
            margin-top: 1.5rem;
        }
        .install-button:hover {
            opacity: 0.7;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>timezone bot</h1>
        <p class="description">automatically convert times to your preferred timezone in slack conversations</p>
        
        <div class="features">
            <h3>features</h3>
            <ul>
                <li>automatic time conversion: detects times in messages and shows them in your timezone</li>
                <li>personal timezone settings: set your preferred timezone once and forget about it</li>
                <li>multiple format support: works with 12-hour, 24-hour, and timezone-specific formats</li>
                <li>simple commands: easy slash commands to manage your timezone preferences</li>
                <li>cross-platform: works seamlessly across all slack clients</li>
            </ul>
        </div>
        
        <p>ready to never miss a meeting due to timezone confusion again?</p>
        
        <a href="https://slack.com/oauth/v2/authorize?client_id={{ client_id }}&scope=app_mentions:read,channels:history,chat:write,commands&user_scope=&redirect_uri={{ redirect_uri }}" class="install-button">
            add to slack →
        </a>
    </div>
</body>
</html>
"""

def save_team_token(team_id, access_token, bot_user_id):
    """Save the team's access token to a JSON file"""
    tokens_file = 'team_tokens.json'
    
    try:
        # Load existing tokens
        tokens = {}
        if os.path.exists(tokens_file):
            try:
                with open(tokens_file, 'r') as f:
                    tokens = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse {tokens_file}, starting with empty tokens")
                tokens = {}
        
        # Save new token
        tokens[team_id] = {
            'access_token': access_token,
            'bot_user_id': bot_user_id,
            'installed_at': str(os.times())
        }
        
        # Write back to file
        with open(tokens_file, 'w') as f:
            json.dump(tokens, f, indent=2)
            
        print(f"Successfully saved token for team {team_id}")
        return True
        
    except Exception as e:
        print(f"Error saving team token: {e}")
        return False

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
        
        print(f"OAuth response: team_id={team_id}, bot_user_id={bot_user_id}, has_token={bool(access_token)}")
        
        if not all([team_id, access_token, bot_user_id]):
            print(f"Missing required OAuth data: team_id={team_id}, access_token={bool(access_token)}, bot_user_id={bot_user_id}")
            return redirect('/error')
        
        # Save the team's token
        if not save_team_token(team_id, access_token, bot_user_id):
            print(f"Failed to save token for team {team_id}")
            return redirect('/error')
        
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

@app.route('/status')
def status():
    """Show installation status"""
    tokens_file = 'team_tokens.json'
    
    if not os.path.exists(tokens_file):
        return {'installed_teams': 0, 'teams': []}
    
    try:
        with open(tokens_file, 'r') as f:
            tokens = json.load(f)
        
        team_list = []
        for team_id, data in tokens.items():
            team_list.append({
                'team_id': team_id,
                'bot_user_id': data.get('bot_user_id'),
                'has_token': bool(data.get('access_token'))
            })
        
        return {
            'installed_teams': len(tokens),
            'teams': team_list
        }
    except Exception as e:
        return {'error': str(e)}

if __name__ == '__main__':
    # Check required environment variables
    if not SLACK_CLIENT_ID or not SLACK_CLIENT_SECRET:
        print("Error: SLACK_CLIENT_ID and SLACK_CLIENT_SECRET must be set in environment variables")
        exit(1)
    
    print("Starting OAuth server...")
    print(f"Install URL: http://localhost:8944/install")
    print(f"OAuth Redirect URI: {SLACK_REDIRECT_URI}")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=8944, debug=True)
