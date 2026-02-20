"""
Tests for Data Isolation Utilities.
"""

from django.test import TestCase, RequestFactory
from django.conf import settings
from django.contrib.auth.models import User
from django.http import JsonResponse
import os
import shutil
import json
from mongoengine import connect, disconnect

from core.models import Bot, BotConfig
from core.data_isolation import get_bot_data_path, ensure_bot_data_access, bot_access_required, create_isolated_directory

class DataIsolationTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Disconnect any existing connections and connect to the test database
        disconnect()
        connect(
            db=settings.MONGODB_SETTINGS['db'],
            host=settings.MONGODB_SETTINGS['host'],
            port=settings.MONGODB_SETTINGS['port'],
            username=settings.MONGODB_SETTINGS.get('username'),
            password=settings.MONGODB_SETTINGS.get('password'),
            authentication_source=settings.MONGODB_SETTINGS.get('authentication_source'),
            alias='default'
        )

    @classmethod
    def tearDownClass(cls):
        # Disconnect after all tests are done
        disconnect(alias='default')
        super().tearDownClass()

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        self.user1 = User.objects.create_user(username='user1', password='password')
        self.user2 = User.objects.create_user(username='user2', password='password')

        # Mock wallet addresses on user objects
        self.user1.wallet_address = 'wallet1'
        self.user2.wallet_address = 'wallet2'

        self.bot1 = Bot.objects.create(
            name="TestBot1",
            owner_wallet_address=self.user1.wallet_address,
            owner_telegram_id=12345,
            config=BotConfig(telegram_token='token1', telegram_username='testbot1')
        )

        self.bot2 = Bot.objects.create(
            name="TestBot2",
            owner_wallet_address=self.user2.wallet_address,
            owner_telegram_id=67890,
            config=BotConfig(telegram_token='token2', telegram_username='testbot2')
        )
        
        # Ensure data dir exists
        self.data_dir = os.path.join(settings.DATA_DIR, 'bots')
        if os.path.exists(self.data_dir):
            shutil.rmtree(self.data_dir)
        os.makedirs(self.data_dir)

    def tearDown(self):
        """Clean up test data."""
        Bot.objects.all().delete()
        User.objects.all().delete()
        if os.path.exists(self.data_dir):
            shutil.rmtree(self.data_dir)

    def test_get_bot_data_path(self):
        """Test the get_bot_data_path function."""
        expected_path_bot = os.path.join(settings.DATA_DIR, 'bots', self.bot1.bot_id)
        self.assertEqual(get_bot_data_path(self.bot1.bot_id), expected_path_bot)

        expected_path_user = os.path.join(settings.DATA_DIR, 'bots', self.bot1.bot_id, 'users', 'user123')
        self.assertEqual(get_bot_data_path(self.bot1.bot_id, 'user123'), expected_path_user)
        
    def test_create_isolated_directory(self):
        """Test that create_isolated_directory creates a directory."""
        path = get_bot_data_path(self.bot1.bot_id, 'user123')
        self.assertFalse(os.path.exists(path))
        create_isolated_directory(path)
        self.assertTrue(os.path.exists(path))

    def test_ensure_bot_data_access(self):
        """Test the ensure_bot_data_access function."""
        # User 1 tries to access Bot 1 (should be allowed)
        request = self.factory.get('/')
        request.user = self.user1
        self.assertTrue(ensure_bot_data_access(request, self.bot1.bot_id))

        # User 2 tries to access Bot 1 (should be denied)
        request.user = self.user2
        self.assertFalse(ensure_bot_data_access(request, self.bot1.bot_id))

        # Test with a non-existent bot
        self.assertFalse(ensure_bot_data_access(request, 'non-existent-bot-id'))

        # Test with user that has no wallet_address
        request.user = User.objects.create_user(username='user3')
        self.assertFalse(ensure_bot_data_access(request, self.bot1.bot_id))
        
    def test_bot_access_required_decorator(self):
        """Test the @bot_access_required decorator."""

        # Define a dummy view
        @bot_access_required
        def dummy_view(request, bot_id):
            return JsonResponse({'success': True})

        # User 1 tries to access Bot 1's view (should be allowed)
        request = self.factory.get(f'/some/path/{self.bot1.bot_id}/')
        request.user = self.user1
        response = dummy_view(request, self.bot1.bot_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {'success': True})
        
        # User 2 tries to access Bot 1's view (should be denied)
        request = self.factory.get(f'/some/path/{self.bot1.bot_id}/')
        request.user = self.user2
        response = dummy_view(request, self.bot1.bot_id)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(json.loads(response.content), {'error': 'Forbidden: You do not have access to this bot.'}) 