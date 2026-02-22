"""
Tests for Personalities app.
"""

import json
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock

from .models import (
    Personality,
    PersonalityCategory,
    PersonalityCategoryMembership,
    PersonalityRating,
    PersonalityTemplate
)


class PersonalityModelTest(TestCase):
    """Test Personality model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = PersonalityCategory.objects.create(
            name='Test Category',
            description='A test category',
            color='#FF0000'
        )
        
        self.personality = Personality.objects.create(
            name='Test Personality',
            description='A test personality',
            creator=self.user,
            system_prompt='You are a helpful assistant.',
            price_ia_coin=Decimal('10.00')
        )
        
        # Add to category
        PersonalityCategoryMembership.objects.create(
            personality=self.personality,
            category=self.category
        )
    
    def test_personality_creation(self):
        """Test personality creation and basic properties."""
        self.assertEqual(self.personality.name, 'Test Personality')
        self.assertEqual(self.personality.creator, self.user)
        self.assertFalse(self.personality.is_free)
        self.assertTrue(self.personality.personality_id)
        self.assertEqual(self.personality.total_installations, 0)
        self.assertEqual(self.personality.total_revenue, 0)
    
    def test_free_personality(self):
        """Test free personality detection."""
        free_personality = Personality.objects.create(
            name='Free Personality',
            description='A free personality',
            creator=self.user,
            system_prompt='You are free.',
            price_ia_coin=Decimal('0.00')
        )
        self.assertTrue(free_personality.is_free)
    
    def test_personality_categories(self):
        """Test personality category relationships."""
        categories = self.personality.categories.all()
        self.assertEqual(categories.count(), 1)
        self.assertEqual(categories.first(), self.category)
    
    def test_personality_validation(self):
        """Test personality validation."""
        # Valid personality
        self.assertTrue(self.personality.validate())
        
        # Invalid system prompt
        self.personality.system_prompt = ''
        self.assertFalse(self.personality.validate())
        
        # Invalid price
        self.personality.system_prompt = 'Valid prompt'
        self.personality.price_ia_coin = Decimal('-1.00')
        self.assertFalse(self.personality.validate())
    
    def test_average_rating(self):
        """Test average rating calculation."""
        # No ratings yet
        self.assertEqual(self.personality.average_rating, 0)
        
        # Add some ratings
        PersonalityRating.objects.create(
            personality=self.personality,
            user=self.user,
            rating=5
        )
        
        user2 = User.objects.create_user(
            username='user2',
            password='pass123'
        )
        PersonalityRating.objects.create(
            personality=self.personality,
            user=user2,
            rating=3
        )
        
        # Should be (5 + 3) / 2 = 4.0
        self.assertEqual(self.personality.average_rating, 4.0)
    
    def test_popularity_score(self):
        """Test popularity score calculation."""
        # Initially should be low
        initial_score = self.personality.popularity_score
        self.assertGreaterEqual(initial_score, 0)
        self.assertLessEqual(initial_score, 10)
        
        # Add ratings and installations
        PersonalityRating.objects.create(
            personality=self.personality,
            user=self.user,
            rating=5
        )
        self.personality.total_installations = 100
        self.personality.save()
        
        # Score should increase
        new_score = self.personality.popularity_score
        self.assertGreater(new_score, initial_score)
    
    @patch('apps.personalities.models.Personality.install_on_bot')
    def test_can_install(self, mock_install):
        """Test can_install method."""
        mock_install.return_value = {'success': True}
        
        # Should be able to install if validation passes
        self.assertTrue(self.personality.can_install(self.user))
        
        # Should not be able to install if validation fails
        mock_install.return_value = {'success': False, 'error': 'Insufficient funds'}
        self.assertFalse(self.personality.can_install(self.user))


class PersonalityCategoryModelTest(TestCase):
    """Test PersonalityCategory model."""
    
    def test_category_creation(self):
        """Test category creation."""
        category = PersonalityCategory.objects.create(
            name='AI Assistants',
            description='Helpful AI assistants',
            color='#00FF00'
        )
        
        self.assertEqual(category.name, 'AI Assistants')
        self.assertEqual(category.color, '#00FF00')
        self.assertEqual(category.icon, '🤖')
        self.assertTrue(category.is_active)
        self.assertEqual(category.sort_order, 0)


class PersonalityTemplateModelTest(TestCase):
    """Test PersonalityTemplate model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.category = PersonalityCategory.objects.create(
            name='Assistant',
            description='Assistant personalities'
        )
        
        self.template = PersonalityTemplate.objects.create(
            name='Basic Assistant',
            description='A basic assistant template',
            category=self.category,
            system_prompt_template='You are a {role} assistant specialized in {domain}.',
            metadata_template={'role': 'helpful', 'domain': 'general'}
        )
    
    def test_template_creation(self):
        """Test template creation."""
        self.assertEqual(self.template.name, 'Basic Assistant')
        self.assertEqual(self.template.category, self.category)
        self.assertEqual(self.template.usage_count, 0)
    
    def test_create_personality_from_template(self):
        """Test creating personality from template."""
        personality = self.template.create_personality(
            creator=self.user,
            name='My Assistant',
            description='My custom assistant',
            role='coding',
            domain='Python programming'
        )
        
        self.assertEqual(personality.name, 'My Assistant')
        self.assertEqual(personality.creator, self.user)
        self.assertIn('coding', personality.system_prompt)
        self.assertIn('Python programming', personality.system_prompt)
        
        # Usage count should increment
        self.template.refresh_from_db()
        self.assertEqual(self.template.usage_count, 1)


class PersonalityAPITest(APITestCase):
    """Test Personality API endpoints."""
    
    def setUp(self):
        """Set up test data."""
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
        
        self.category = PersonalityCategory.objects.create(
            name='Test Category',
            description='A test category'
        )
        
        self.personality = Personality.objects.create(
            name='Test Personality',
            description='A test personality',
            creator=self.user,
            system_prompt='You are helpful.',
            price_ia_coin=Decimal('10.00'),
            is_public=True
        )
        
        PersonalityCategoryMembership.objects.create(
            personality=self.personality,
            category=self.category
        )
    
    def test_list_personalities(self):
        """Test listing personalities."""
        url = reverse('personalities:personality-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Personality')
    
    def test_get_personality_detail(self):
        """Test getting personality details."""
        url = reverse('personalities:personality-detail', args=[self.personality.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Personality')
        self.assertEqual(response.data['creator_username'], 'testuser')
    
    def test_create_personality_authenticated(self):
        """Test creating personality when authenticated."""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('personalities:personality-list')
        data = {
            'name': 'New Personality',
            'description': 'A new personality',
            'system_prompt': 'You are new.',
            'price_ia_coin': '5.00',
            'category_ids': [self.category.id]
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check personality was created
        personality = Personality.objects.get(name='New Personality')
        self.assertEqual(personality.creator, self.user)
        self.assertEqual(personality.categories.count(), 1)
    
    def test_create_personality_unauthenticated(self):
        """Test creating personality when not authenticated."""
        url = reverse('personalities:personality-list')
        data = {
            'name': 'New Personality',
            'description': 'A new personality',
            'system_prompt': 'You are new.',
            'price_ia_coin': '5.00'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    @patch('apps.personalities.models.Personality.install_on_bot')
    def test_install_personality(self, mock_install):
        """Test installing personality on bot."""
        self.client.force_authenticate(user=self.user)
        mock_install.return_value = {
            'success': True,
            'installation_id': 'inst_123',
            'cost': 10
        }
        
        url = reverse('personalities:personality-install', args=[self.personality.id])
        data = {
            'bot_passport_id': 'bot_123',
            'custom_prompt_override': 'Custom prompt'
        }
        
        with patch('apps.personalities.serializers.BotPassport') as mock_passport:
            # Mock the passport validation
            mock_passport.objects.get.return_value = MagicMock()
            
            response = self.client.post(url, data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data['success'])
            self.assertEqual(response.data['cost'], 10)
    
    def test_rate_personality(self):
        """Test rating a personality."""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('personalities:personality-rate', args=[self.personality.id])
        data = {
            'rating': 5,
            'review': 'Excellent personality!'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check rating was created
        rating = PersonalityRating.objects.get(
            personality=self.personality,
            user=self.user
        )
        self.assertEqual(rating.rating, 5)
        self.assertEqual(rating.review, 'Excellent personality!')
    
    def test_update_existing_rating(self):
        """Test updating an existing rating."""
        self.client.force_authenticate(user=self.user)
        
        # Create initial rating
        PersonalityRating.objects.create(
            personality=self.personality,
            user=self.user,
            rating=3,
            review='OK'
        )
        
        url = reverse('personalities:personality-rate', args=[self.personality.id])
        data = {
            'rating': 5,
            'review': 'Much better now!'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check rating was updated
        rating = PersonalityRating.objects.get(
            personality=self.personality,
            user=self.user
        )
        self.assertEqual(rating.rating, 5)
        self.assertEqual(rating.review, 'Much better now!')
    
    def test_search_personalities(self):
        """Test personality search."""
        url = reverse('personalities:personality-search')
        data = {
            'query': 'test',
            'category_ids': [self.category.id],
            'max_price': 20,
            'sort_by': 'name',
            'sort_order': 'asc'
        }
        
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_get_my_personalities(self):
        """Test getting user's own personalities."""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('personalities:personality-my-personalities')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_get_featured_personalities(self):
        """Test getting featured personalities."""
        # Make personality featured
        self.personality.total_installations = 150
        self.personality.popularity_score = 8.5
        self.personality.save()
        
        url = reverse('personalities:personality-featured')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class PersonalityCategoryAPITest(APITestCase):
    """Test PersonalityCategory API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.category = PersonalityCategory.objects.create(
            name='Test Category',
            description='A test category',
            color='#FF0000'
        )
    
    def test_list_categories(self):
        """Test listing categories."""
        url = reverse('personalities:personality-category-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Category')
    
    def test_get_category_personalities(self):
        """Test getting personalities in a category."""
        # Create personality in category
        user = User.objects.create_user(username='test', password='test')
        personality = Personality.objects.create(
            name='Test Personality',
            creator=user,
            system_prompt='Test',
            is_public=True
        )
        PersonalityCategoryMembership.objects.create(
            personality=personality,
            category=self.category
        )
        
        url = reverse('personalities:personality-category-personalities', args=[self.category.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class PersonalityTemplateAPITest(APITestCase):
    """Test PersonalityTemplate API endpoints."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.category = PersonalityCategory.objects.create(
            name='Assistant',
            description='Assistant personalities'
        )
        
        self.template = PersonalityTemplate.objects.create(
            name='Basic Assistant',
            description='A basic assistant template',
            category=self.category,
            system_prompt_template='You are a {role} assistant.',
            metadata_template={'role': 'helpful'}
        )
    
    def test_list_templates(self):
        """Test listing templates."""
        url = reverse('personalities:personality-template-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_use_template(self):
        """Test using a template to create personality."""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('personalities:personality-template-use-template', args=[self.template.id])
        data = {
            'name': 'My Assistant',
            'description': 'My custom assistant',
            'custom_values': {'role': 'coding'}
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Check personality was created
        personality = Personality.objects.get(name='My Assistant')
        self.assertEqual(personality.creator, self.user)
        self.assertIn('coding', personality.system_prompt)