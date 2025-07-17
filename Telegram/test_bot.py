#!/usr/bin/env python3
"""
Test script to verify Telegram bot token and basic functionality
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

def test_bot_token():
    """Test if the bot token is valid"""
    try:
        import telebot
        
        token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not token:
            print("❌ TELEGRAM_BOT_TOKEN is not set")
            return False
        
        print(f"✅ Bot token found: {token[:10]}...")
        
        # Test bot initialization
        bot = telebot.TeleBot(token)
        
        # Test API call
        me = bot.get_me()
        print(f"✅ Bot authenticated: @{me.username}")
        print(f"   Bot ID: {me.id}")
        print(f"   Bot name: {me.first_name}")
        
        return True
        
    except ImportError:
        print("❌ telebot package not found. Install with: pip install pyTelegramBotAPI")
        return False
    except Exception as e:
        print(f"❌ Bot authentication failed: {e}")
        return False

def test_dependencies():
    """Test if all required dependencies are available"""
    dependencies = [
        'telebot',
        'pytz', 
        'flask',
        'requests',
        'dotenv'
    ]
    
    missing = []
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✅ {dep} available")
        except ImportError:
            print(f"❌ {dep} missing")
            missing.append(dep)
    
    if missing:
        print(f"\n❌ Missing dependencies: {', '.join(missing)}")
        print("Install with: pip install pyTelegramBotAPI pytz flask requests python-dotenv")
        return False
    
    return True

def main():
    print("Telegram Bot Test")
    print("=" * 50)
    
    deps_ok = test_dependencies()
    if not deps_ok:
        sys.exit(1)
    
    print("\n" + "=" * 50)
    
    token_ok = test_bot_token()
    if not token_ok:
        sys.exit(1)
    
    print("\n✅ All tests passed! Bot should work correctly.")

if __name__ == "__main__":
    main()
