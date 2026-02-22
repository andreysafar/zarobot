"""
Tests for skills app
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal

from .models import SkillCategory, Skill, SkillInstallation, SkillRating
from apps.bot_core.models import BotPassport


class SkillCategoryModelTest(TestCase):
    """Тесты модели SkillCategory"""
    
    def setUp(self):
        self.category = SkillCategory.objects.create(
            name="Разработка",
            description="Навыки для разработки",
            icon="💻",
            color="#FF5722"
        )
    
    def test_category_creation(self):
        """Тест создания категории"""
        self.assertEqual(self.category.name, "Разработка")
        self.assertEqual(self.category.icon, "💻")
        self.assertTrue(self.category.is_active)
    
    def test_category_str(self):
        """Тест строкового представления"""
        self.assertEqual(str(self.category), "💻 Разработка")


class SkillModelTest(TestCase):
    """Тесты модели Skill"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testcreator',
            email='test@example.com',
            password='testpass123'
        )
        self.category = SkillCategory.objects.create(
            name="Разработка",
            icon="💻"
        )
        self.skill = Skill.objects.create(
            name="Python Code Generator",
            description="Generates Python code using AI",
            version="1.0.0",
            creator=self.user,
            category=self.category,
            price_ia_coins=Decimal('25.00'),
            execution_type='api_call',
            api_endpoint='https://api.example.com/generate'
        )
    
    def test_skill_creation(self):
        """Тест создания навыка"""
        self.assertEqual(self.skill.name, "Python Code Generator")
        self.assertEqual(self.skill.creator, self.user)
        self.assertEqual(self.skill.status, 'draft')
        self.assertFalse(self.skill.is_public)
        self.assertEqual(self.skill.price_ia_coins, Decimal('25.00'))
    
    def test_skill_str(self):
        """Тест строкового представления"""
        self.assertEqual(str(self.skill), "Python Code Generator v1.0.0")
    
    def test_popularity_score(self):
        """Тест расчета популярности"""
        # Начальная популярность
        self.assertEqual(self.skill.popularity_score, 0.0)
        
        # Добавляем статистику
        self.skill.total_installations = 100
        self.skill.average_rating = Decimal('4.5')
        self.skill.total_revenue = Decimal('1000.00')
        
        popularity = self.skill.popularity_score
        self.assertGreater(popularity, 0)
        self.assertLessEqual(popularity, 10.0)
    
    def test_can_install(self):
        """Тест проверки возможности установки"""
        # Черновик - нельзя установить
        self.assertFalse(self.skill.can_install(self.user))
        
        # Активный публичный навык - можно установить
        self.skill.status = 'active'
        self.skill.is_public = True
        self.assertTrue(self.skill.can_install(self.user))


class SkillInstallationModelTest(TestCase):
    """Тесты модели SkillInstallation"""
    
    def setUp(self):
        self.creator = User.objects.create_user(
            username='creator',
            password='pass123'
        )
        self.buyer = User.objects.create_user(
            username='buyer',
            password='pass123'
        )
        self.skill = Skill.objects.create(
            name="Test Skill",
            creator=self.creator,
            price_ia_coins=Decimal('10.00')
        )
        self.bot = BotPassport.objects.create(
            name="Test Bot",
            owner=self.buyer
        )
        self.installation = SkillInstallation.objects.create(
            skill=self.skill,
            bot_passport=self.bot,
            buyer=self.buyer,
            price_paid=Decimal('10.00')
        )
    
    def test_installation_creation(self):
        """Тест создания установки"""
        self.assertEqual(self.installation.skill, self.skill)
        self.assertEqual(self.installation.buyer, self.buyer)
        self.assertEqual(self.installation.status, 'pending')
        self.assertTrue(self.installation.is_enabled)
    
    def test_installation_str(self):
        """Тест строкового представления"""
        expected = f"{self.skill.name} on {self.bot.name}"
        self.assertEqual(str(self.installation), expected)


class SkillRatingModelTest(TestCase):
    """Тесты модели SkillRating"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='rater',
            password='pass123'
        )
        self.creator = User.objects.create_user(
            username='creator',
            password='pass123'
        )
        self.skill = Skill.objects.create(
            name="Test Skill",
            creator=self.creator
        )
        self.rating = SkillRating.objects.create(
            skill=self.skill,
            user=self.user,
            rating=5,
            review="Excellent skill!"
        )
    
    def test_rating_creation(self):
        """Тест создания оценки"""
        self.assertEqual(self.rating.skill, self.skill)
        self.assertEqual(self.rating.user, self.user)
        self.assertEqual(self.rating.rating, 5)
        self.assertEqual(self.rating.review, "Excellent skill!")
    
    def test_rating_str(self):
        """Тест строкового представления"""
        expected = f"{self.user.username}: 5★ for {self.skill.name}"
        self.assertEqual(str(self.rating), expected)


class SkillAPITest(APITestCase):
    """Тесты API навыков"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.category = SkillCategory.objects.create(
            name="Test Category",
            icon="🧪"
        )
        self.skill = Skill.objects.create(
            name="Test Skill",
            description="A test skill",
            creator=self.user,
            category=self.category,
            price_ia_coins=Decimal('15.00'),
            status='active',
            is_public=True
        )
    
    def test_skill_list(self):
        """Тест получения списка навыков"""
        url = reverse('skills:skill-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Skill')
    
    def test_skill_create_authenticated(self):
        """Тест создания навыка аутентифицированным пользователем"""
        self.client.force_authenticate(user=self.user)
        url = reverse('skills:skill-list')
        data = {
            'name': 'New Skill',
            'description': 'A new skill',
            'version': '1.0.0',
            'category': self.category.id,
            'price_ia_coins': '20.00',
            'execution_type': 'api_call',
            'api_endpoint': 'https://api.example.com/skill'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Skill')
        self.assertEqual(response.data['creator']['username'], self.user.username)
    
    def test_skill_create_unauthenticated(self):
        """Тест создания навыка неаутентифицированным пользователем"""
        url = reverse('skills:skill-list')
        data = {
            'name': 'New Skill',
            'description': 'A new skill'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_skill_detail(self):
        """Тест получения детальной информации о навыке"""
        url = reverse('skills:skill-detail', args=[self.skill.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.skill.name)
        self.assertEqual(response.data['description'], self.skill.description)
    
    def test_skill_search(self):
        """Тест поиска навыков"""
        url = reverse('skills:skill-search')
        data = {
            'query': 'test',
            'category': self.category.id,
            'sort_by': 'name'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_skill_featured(self):
        """Тест получения популярных навыков"""
        url = reverse('skills:skill-featured')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_my_skills_authenticated(self):
        """Тест получения навыков пользователя"""
        self.client.force_authenticate(user=self.user)
        url = reverse('skills:skill-my-skills')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_my_skills_unauthenticated(self):
        """Тест получения навыков неаутентифицированным пользователем"""
        url = reverse('skills:skill-my-skills')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SkillCategoryAPITest(APITestCase):
    """Тесты API категорий навыков"""
    
    def setUp(self):
        self.category = SkillCategory.objects.create(
            name="Development",
            description="Development skills",
            icon="💻"
        )
    
    def test_category_list(self):
        """Тест получения списка категорий"""
        url = reverse('skills:skill-category-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Development')
    
    def test_category_skills(self):
        """Тест получения навыков категории"""
        # Создаем навык в категории
        user = User.objects.create_user(username='creator', password='pass')
        Skill.objects.create(
            name="Category Skill",
            creator=user,
            category=self.category,
            status='active',
            is_public=True
        )
        
        url = reverse('skills:skill-category-skills', args=[self.category.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Category Skill')


class SkillInstallationAPITest(APITestCase):
    """Тесты API установок навыков"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='buyer',
            password='pass123'
        )
        self.creator = User.objects.create_user(
            username='creator',
            password='pass123'
        )
        self.skill = Skill.objects.create(
            name="Installable Skill",
            creator=self.creator,
            status='active',
            is_public=True,
            price_ia_coins=Decimal('10.00')
        )
        self.bot = BotPassport.objects.create(
            name="User Bot",
            owner=self.user
        )
    
    def test_skill_install_authenticated(self):
        """Тест установки навыка аутентифицированным пользователем"""
        self.client.force_authenticate(user=self.user)
        url = reverse('skills:skill-install', args=[self.skill.id])
        data = {
            'bot_passport_id': str(self.bot.id),
            'config': {'param1': 'value1'}
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['skill']['name'], self.skill.name)
    
    def test_skill_install_unauthenticated(self):
        """Тест установки навыка неаутентифицированным пользователем"""
        url = reverse('skills:skill-install', args=[self.skill.id])
        data = {'bot_passport_id': str(self.bot.id)}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_installation_list_authenticated(self):
        """Тест получения списка установок пользователя"""
        # Создаем установку
        installation = SkillInstallation.objects.create(
            skill=self.skill,
            bot_passport=self.bot,
            buyer=self.user,
            price_paid=Decimal('10.00')
        )
        
        self.client.force_authenticate(user=self.user)
        url = reverse('skills:skill-installation-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class SkillRatingAPITest(APITestCase):
    """Тесты API оценок навыков"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='rater',
            password='pass123'
        )
        self.creator = User.objects.create_user(
            username='creator',
            password='pass123'
        )
        self.skill = Skill.objects.create(
            name="Ratable Skill",
            creator=self.creator,
            status='active',
            is_public=True
        )
        self.bot = BotPassport.objects.create(
            name="User Bot",
            owner=self.user
        )
        # Создаем установку для возможности оценки
        self.installation = SkillInstallation.objects.create(
            skill=self.skill,
            bot_passport=self.bot,
            buyer=self.user,
            price_paid=Decimal('0.00'),
            status='completed'
        )
    
    def test_skill_rate_authenticated(self):
        """Тест оценки навыка аутентифицированным пользователем"""
        self.client.force_authenticate(user=self.user)
        url = reverse('skills:skill-rate', args=[self.skill.id])
        data = {
            'rating': 5,
            'review': 'Excellent skill!'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['rating'], 5)
        self.assertEqual(response.data['review'], 'Excellent skill!')
    
    def test_skill_rate_unauthenticated(self):
        """Тест оценки навыка неаутентифицированным пользователем"""
        url = reverse('skills:skill-rate', args=[self.skill.id])
        data = {'rating': 5}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)