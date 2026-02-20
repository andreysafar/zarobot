#!/usr/bin/env python
"""
Test script to verify MongoDB and Redis connections.
Run this to ensure database setup is working correctly.
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
sys.path.append(str(Path(__file__).resolve().parent))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.core.cache import cache
from core.models import Bot, BotConfig, UserSession
from config.tokenomics import validate_economic_rules
import mongoengine
import redis


def test_mongodb_connection():
    """Test MongoDB connection and basic operations."""
    print("🔍 Testing MongoDB connection...")
    
    try:
        # Test connection
        from mongoengine.connection import get_db
        db = get_db()
        
        # Test basic operation
        collections = db.list_collection_names()
        print(f"✅ MongoDB connected successfully!")
        print(f"   Database: {db.name}")
        print(f"   Collections: {len(collections)}")
        
        # Test model creation
        print("\n🔍 Testing model operations...")
        
        # Create a test bot
        test_config = BotConfig(
            personality='iya',
            telegram_token='test_token_123',
            telegram_username='test_bot'
        )
        
        test_bot = Bot(
            name='Test Bot',
            description='Test bot for connection verification',
            owner_wallet_address='test_wallet_123',
            owner_telegram_id=123456789,
            config=test_config
        )
        
        # Save and retrieve
        test_bot.save()
        print(f"✅ Created test bot with bot_id: {test_bot.bot_id}")
        
        # Test data isolation path
        data_path = test_bot.get_data_path('test_user_123')
        print(f"✅ Data isolation path: {data_path}")
        
        # Test retrieval
        retrieved_bot = Bot.get_by_bot_id(test_bot.bot_id)
        if retrieved_bot:
            print(f"✅ Successfully retrieved bot: {retrieved_bot.name}")
        
        # Clean up
        test_bot.delete()
        print("✅ Test bot cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        return False


def test_redis_connection():
    """Test Redis connection and caching."""
    print("\n🔍 Testing Redis connection...")
    
    try:
        # Test Django cache (Redis)
        cache.set('test_key', 'test_value', 30)
        cached_value = cache.get('test_key')
        
        if cached_value == 'test_value':
            print("✅ Django Redis cache working!")
        else:
            print("❌ Django Redis cache not working")
            return False
        
        # Test direct Redis connection
        from django.conf import settings
        redis_settings = settings.REDIS_SETTINGS
        
        r = redis.Redis(
            host=redis_settings['host'],
            port=redis_settings['port'],
            db=redis_settings['db'],
            password=redis_settings['password']
        )
        
        # Test ping
        if r.ping():
            print("✅ Direct Redis connection working!")
        else:
            print("❌ Direct Redis connection failed")
            return False
        
        # Test basic operations
        r.set('zero_bot_test', 'connection_test', ex=30)
        test_value = r.get('zero_bot_test')
        
        if test_value and test_value.decode() == 'connection_test':
            print("✅ Redis operations working!")
        else:
            print("❌ Redis operations failed")
            return False
        
        # Clean up
        r.delete('zero_bot_test')
        cache.delete('test_key')
        
        return True
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False


def test_user_session():
    """Test user session creation with data isolation."""
    print("\n🔍 Testing user session with data isolation...")
    
    try:
        # Create test bot first
        test_config = BotConfig(
            personality='iya',
            telegram_token='session_test_token',
            telegram_username='session_test_bot'
        )
        
        test_bot = Bot(
            name='Session Test Bot',
            description='Bot for session testing',
            owner_wallet_address='session_test_wallet',
            owner_telegram_id=987654321,
            config=test_config
        )
        test_bot.save()
        
        # Create user session
        session, created = UserSession.get_or_create_session(
            bot_id=test_bot.bot_id,
            user_id='test_user_456',
            telegram_username='test_user',
            first_name='Test',
            last_name='User'
        )
        
        if created:
            print(f"✅ Created new user session: {session.session_id}")
        else:
            print(f"✅ Retrieved existing session: {session.session_id}")
        
        # Test data path
        data_path = session.get_data_path()
        expected_path = f"/data/bots/{test_bot.bot_id}/users/test_user_456/"
        
        if data_path == expected_path:
            print(f"✅ Data isolation path correct: {data_path}")
        else:
            print(f"❌ Data isolation path incorrect: {data_path}")
            return False
        
        # Clean up
        session.delete()
        test_bot.delete()
        print("✅ Session test cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ User session test failed: {e}")
        return False


def test_economic_rules():
    """Test economic rules validation."""
    print("\n🔍 Testing economic rules validation...")
    
    try:
        validate_economic_rules()
        print("✅ Economic rules validation passed!")
        return True
    except Exception as e:
        print(f"❌ Economic rules validation failed: {e}")
        return False


def main():
    """Run all connection tests."""
    print("🚀 Zero-Bot Database Connection Tests")
    print("=" * 50)
    
    tests = [
        ("MongoDB Connection", test_mongodb_connection),
        ("Redis Connection", test_redis_connection),
        ("User Session & Data Isolation", test_user_session),
        ("Economic Rules", test_economic_rules),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        print("-" * 30)
        result = test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("\n🎉 All tests passed! Database setup is working correctly.")
        return True
    else:
        print(f"\n⚠️  {len(tests) - passed} test(s) failed. Please check your configuration.")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1) 