"""
Tests for Bot Core models and views.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from .models import BotPassport, BotState, SkillInstallation, PersonalityInstance


class BotPassportModelTest(TestCase):
    """Test Bot Passport model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_bot_passport_creation(self):
        """Test creating a bot passport."""
        passport = BotPassport.objects.create(
            name='Test Bot',
            description='A test bot',
            owner=self.user
        )
        
        self.assertEqual(passport.name, 'Test Bot')
        self.assertEqual(passport.owner, self.user)
        self.assertEqual(passport.training_level, 1)
        self.assertEqual(passport.experience_points, 0)
        self.assertTrue(passport.is_active)
    
    def test_experience_and_leveling(self):
        """Test experience points and leveling system."""
        passport = BotPassport.objects.create(
            name='Test Bot',
            owner=self.user
        )
        
        # Initial state
        self.assertEqual(passport.training_level, 1)
        self.assertEqual(passport.experience_points, 0)
        self.assertFalse(passport.can_level_up())
        
        # Add experience (not enough to level up)
        passport.add_experience(50)
        self.assertEqual(passport.experience_points, 50)
        self.assertEqual(passport.training_level, 1)
        
        # Add more experience (enough to level up)
        passport.add_experience(50)
        self.assertEqual(passport.experience_points, 100)
        self.assertEqual(passport.training_level, 2)
    
    def test_training_progress(self):
        """Test training progress calculation."""
        passport = BotPassport.objects.create(
            name='Test Bot',
            owner=self.user
        )
        
        # At level 1 with 50 XP (50% progress to level 2)
        passport.experience_points = 50
        progress = passport.get_training_progress()
        self.assertAlmostEqual(progress, 0.5, places=2)
        
        # At level 1 with 100 XP (ready to level up)
        passport.experience_points = 100
        progress = passport.get_training_progress()
        self.assertAlmostEqual(progress, 1.0, places=2)
    
    def test_marketplace_value_multiplier(self):
        """Test marketplace value multiplier calculation."""
        passport = BotPassport.objects.create(
            name='Test Bot',
            owner=self.user,
            training_level=5
        )
        
        # Level 5 should have 1.4x multiplier (1.0 + 4 * 0.1)
        expected_multiplier = 1.4
        self.assertAlmostEqual(passport.marketplace_value_multiplier, expected_multiplier, places=2)


class BotStateModelTest(TestCase):
    """Test Bot State model functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.passport = BotPassport.objects.create(
            name='Test Bot',
            owner=self.user
        )
    
    def test_bot_state_creation(self):
        """Test creating a bot state."""
        state = BotState.objects.create(
            passport=self.passport,
            conversation_context={'last_message': 'Hello'},
            sync_status='pending'
        )
        
        self.assertEqual(state.passport, self.passport)
        self.assertEqual(state.conversation_context['last_message'], 'Hello')
        self.assertEqual(state.sync_status, 'pending')
    
    def test_sync_status_management(self):
        """Test sync status management methods."""
        state = BotState.objects.create(
            passport=self.passport,
            sync_status='synced'
        )
        
        # Mark for sync
        state.mark_for_sync()
        self.assertEqual(state.sync_status, 'pending')
        
        # Mark as synced
        state.mark_synced()
        self.assertEqual(state.sync_status, 'synced')
        self.assertIsNotNone(state.last_synced_at)
        
        # Mark sync error
        state.mark_sync_error()
        self.assertEqual(state.sync_status, 'error')


class BotPassportAPITest(APITestCase):
    """Test Bot Passport API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='testpass123'
        )
        
        # Create test bots
        self.bot1 = BotPassport.objects.create(
            name='Test Bot 1',
            owner=self.user
        )
        self.bot2 = BotPassport.objects.create(
            name='Test Bot 2',
            owner=self.other_user
        )
    
    def test_list_bots_authenticated(self):
        """Test listing bots for authenticated user."""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.get('/api/v1/bot-core/passports/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # User should only see their own bot
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Bot 1')
    
    def test_list_bots_unauthenticated(self):
        """Test listing bots without authentication."""
        response = self.client.get('/api/v1/bot-core/passports/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_bot(self):
        """Test creating a new bot."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'name': 'New Test Bot',
            'description': 'A new test bot',
        }
        
        response = self.client.post('/api/v1/bot-core/passports/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check bot was created with correct owner
        bot = BotPassport.objects.get(name='New Test Bot')
        self.assertEqual(bot.owner, self.user)
        
        # Check bot state was created
        self.assertTrue(hasattr(bot, 'local_state'))
    
    def test_add_experience(self):
        """Test adding experience to a bot."""
        self.client.force_authenticate(user=self.user)
        
        data = {'xp_amount': 75}
        
        response = self.client.post(
            f'/api/v1/bot-core/passports/{self.bot1.bot_id}/add_experience/',
            data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check experience was added
        self.bot1.refresh_from_db()
        self.assertEqual(self.bot1.experience_points, 75)
        
        # Check response data
        self.assertEqual(response.data['experience_points'], 75)
        self.assertFalse(response.data['leveled_up'])
    
    def test_level_up(self):
        """Test manual level up."""
        self.client.force_authenticate(user=self.user)
        
        # Give bot enough XP to level up
        self.bot1.experience_points = 100
        self.bot1.save()
        
        response = self.client.post(
            f'/api/v1/bot-core/passports/{self.bot1.bot_id}/level_up/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check bot leveled up
        self.bot1.refresh_from_db()
        self.assertEqual(self.bot1.training_level, 2)
        
        # Check response data
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['training_level'], 2)
    
    def test_get_bot_state(self):
        """Test getting bot state."""
        self.client.force_authenticate(user=self.user)
        
        # Create bot state
        BotState.objects.create(
            passport=self.bot1,
            conversation_context={'test': 'data'},
            sync_status='synced'
        )
        
        response = self.client.get(
            f'/api/v1/bot-core/passports/{self.bot1.bot_id}/state/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check state data
        self.assertEqual(response.data['conversation_context']['test'], 'data')
        self.assertEqual(response.data['sync_status'], 'synced')