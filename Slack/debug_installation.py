#!/usr/bin/env python3
"""
Debug script to help diagnose Slack bot installation issues
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

def check_environment():
    """Check required environment variables"""
    print("🔍 Checking Environment Variables...")
    
    required_vars = [
        'SLACK_CLIENT_ID',
        'SLACK_CLIENT_SECRET', 
        'SLACK_SIGNING_SECRET',
        'SLACK_REDIRECT_URI'
    ]
    
    optional_vars = [
        'SLACK_BOT_TOKEN'
    ]
    
    all_good = True
    
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {'*' * min(len(value), 8)}...")
        else:
            print(f"❌ {var}: NOT SET")
            all_good = False
    
    for var in optional_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {'*' * min(len(value), 8)}...")
        else:
            print(f"⚠️  {var}: Not set (optional)")
    
    return all_good

def check_tokens():
    """Check saved tokens"""
    print("\n🔍 Checking Saved Tokens...")
    
    tokens_file = 'team_tokens.json'
    if os.path.exists(tokens_file):
        try:
            with open(tokens_file, 'r') as f:
                tokens = json.load(f)
            
            print(f"✅ Found {len(tokens)} installed teams:")
            for team_id, data in tokens.items():
                has_token = bool(data.get('access_token'))
                bot_user_id = data.get('bot_user_id', 'N/A')
                print(f"  - Team {team_id}: token={has_token}, bot_user_id={bot_user_id}")
                
        except Exception as e:
            print(f"❌ Error reading tokens: {e}")
    else:
        print("⚠️  No tokens file found")

def check_servers():
    """Check if servers are running"""
    print("\n🔍 Checking Servers...")
    
    servers = [
        ("OAuth Server", "http://localhost:8944/health"),
        ("Main Bot", "http://localhost:3000/health"),
        ("Production OAuth", "https://slackbot.leonardocerv.hackclub.app/health"),
        ("Production Install", "https://slackbot.leonardocerv.hackclub.app/install")
    ]
    
    for name, url in servers:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {name}: Running")
            else:
                print(f"❌ {name}: HTTP {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"❌ {name}: Not running")
        except Exception as e:
            print(f"❌ {name}: Error - {e}")

def suggest_fixes():
    """Suggest potential fixes"""
    print("\nPotential Fixes:")
    print("1. Make sure your bot is started with 'python app.py'")
    print("2. Verify your SLACK_SIGNING_SECRET is correct")
    print("3. Check that your Request URL in Slack app settings points to your server")
    print("4. Try reinstalling the bot via: https://slackbot.leonardocerv.hackclub.app/install")
    print("5. Check Slack app settings for proper scopes: app_mentions:read, channels:history, chat:write, commands")
    print("6. Verify your app's Event Subscriptions are enabled")
    print("7. Ensure your reverse proxy is forwarding requests to localhost correctly")
    
    print("\nInstallation Process:")
    print("1. Start the bot: python app.py")
    print("2. Visit: https://slackbot.leonardocerv.hackclub.app/install")
    print("3. Click 'Add to Slack' and authorize")
    print("4. Check token was saved: https://slackbot.leonardocerv.hackclub.app/status")
    print("5. Test commands in your Slack workspace")
    
    print("\nSlack App Configuration:")
    print("- Redirect URL: https://slackbot.leonardocerv.hackclub.app/oauth")
    print("- Request URL: https://slackbot.leonardocerv.hackclub.app/slack/events")
    print("- Install URL: https://slackbot.leonardocerv.hackclub.app/install")

def main():
    print("Slack Bot Installation Debugger")
    print("=" * 50)
    
    env_ok = check_environment()
    check_tokens()
    check_servers()
    
    if not env_ok:
        print("\n❌ Environment variables are missing! Please check your .env file.")
    
    suggest_fixes()

if __name__ == "__main__":
    main()
