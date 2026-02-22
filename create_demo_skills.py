#!/usr/bin/env python3
"""
Скрипт для создания демонстрационных навыков и данных
"""

import os
import sys
import django
from pathlib import Path
from decimal import Decimal

# Настройка Django
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from apps.skills.models import SkillCategory, Skill, SkillRating
from apps.bot_core.models import BotPassport

def create_demo_data():
    """Создание демонстрационных данных"""
    
    print("🎯 Создание демонстрационных данных для Skills...")
    
    # 1. Создание пользователей
    print("\n👥 Создание пользователей...")
    
    # Админ
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@zerobot.ai',
            'first_name': 'Zero Bot',
            'last_name': 'Admin',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print(f"✅ Создан админ: {admin_user.username}")
    
    # Разработчики навыков
    developers = [
        ('ai_developer', 'AI Developer', 'ai@dev.com'),
        ('linguist_pro', 'Pro Linguist', 'lang@dev.com'),
        ('code_master', 'Code Master', 'code@dev.com'),
        ('data_scientist', 'Data Scientist', 'data@dev.com'),
    ]
    
    dev_users = []
    for username, name, email in developers:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': name.split()[0],
                'last_name': name.split()[1] if len(name.split()) > 1 else '',
            }
        )
        if created:
            user.set_password('dev123')
            user.save()
            print(f"✅ Создан разработчик: {user.username}")
        dev_users.append(user)
    
    # Тестовый пользователь
    test_user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        }
    )
    if created:
        test_user.set_password('test123')
        test_user.save()
        print(f"✅ Создан тестовый пользователь: {test_user.username}")
    
    # 2. Создание категорий навыков
    print("\n📂 Создание категорий навыков...")
    
    categories_data = [
        ('Разработка', 'Навыки для разработки и программирования', '💻', '#2196F3', 1),
        ('Языки', 'Переводы и работа с языками', '🌍', '#4CAF50', 2),
        ('Анализ', 'Анализ данных и аналитика', '📊', '#FF9800', 3),
        ('Творчество', 'Креативные и художественные навыки', '🎨', '#E91E63', 4),
        ('Утилиты', 'Полезные инструменты и утилиты', '🛠️', '#9C27B0', 5),
        ('Бизнес', 'Бизнес-процессы и автоматизация', '💼', '#607D8B', 6),
    ]
    
    categories = {}
    for name, desc, icon, color, order in categories_data:
        category, created = SkillCategory.objects.get_or_create(
            name=name,
            defaults={
                'description': desc,
                'icon': icon,
                'color': color,
                'sort_order': order,
                'is_active': True
            }
        )
        categories[name] = category
        if created:
            print(f"✅ Создана категория: {icon} {name}")
    
    # 3. Создание навыков
    print("\n🧠 Создание навыков...")
    
    skills_data = [
        {
            'name': 'Генератор Python кода',
            'description': 'Автоматическая генерация качественного Python кода с использованием AI. Поддерживает различные паттерны и стили программирования.',
            'version': '2.1.0',
            'creator': dev_users[0],
            'category': categories['Разработка'],
            'tags': ['python', 'code', 'ai', 'development', 'automation'],
            'price_ia_coins': Decimal('25.00'),
            'execution_type': 'api_call',
            'api_endpoint': 'https://api.codegen.ai/v1/python',
            'config_schema': {
                'language_version': {'type': 'string', 'default': '3.12', 'enum': ['3.8', '3.9', '3.10', '3.11', '3.12']},
                'code_style': {'type': 'string', 'default': 'pep8', 'enum': ['pep8', 'google', 'numpy']},
                'complexity': {'type': 'string', 'default': 'medium', 'enum': ['simple', 'medium', 'complex']},
                'include_tests': {'type': 'boolean', 'default': True},
                'include_docs': {'type': 'boolean', 'default': True}
            },
            'requirements': ['Python 3.8+', 'API ключ CodeGen'],
            'capabilities': ['code_generation', 'syntax_checking', 'code_optimization'],
            'status': 'active',
            'is_public': True
        },
        {
            'name': 'Умный переводчик Pro',
            'description': 'Профессиональный переводчик с поддержкой 50+ языков, контекстным пониманием и специализированными терминологиями.',
            'version': '3.0.2',
            'creator': dev_users[1],
            'category': categories['Языки'],
            'tags': ['translation', 'languages', 'nlp', 'context', 'professional'],
            'price_ia_coins': Decimal('18.00'),
            'execution_type': 'api_call',
            'api_endpoint': 'https://api.translate-pro.ai/v3/translate',
            'config_schema': {
                'source_lang': {'type': 'string', 'default': 'auto'},
                'target_lang': {'type': 'string', 'required': True},
                'formality': {'type': 'string', 'default': 'default', 'enum': ['formal', 'informal', 'default']},
                'preserve_formatting': {'type': 'boolean', 'default': True},
                'terminology': {'type': 'string', 'default': 'general', 'enum': ['general', 'technical', 'medical', 'legal']}
            },
            'requirements': ['Translate Pro API'],
            'capabilities': ['translation', 'language_detection', 'context_analysis'],
            'status': 'active',
            'is_public': True
        },
        {
            'name': 'Анализатор настроения',
            'description': 'Определение эмоционального окраса текста, анализ тональности и настроения пользователя с высокой точностью.',
            'version': '1.5.1',
            'creator': dev_users[2],
            'category': categories['Анализ'],
            'tags': ['sentiment', 'emotion', 'analysis', 'nlp', 'mood'],
            'price_ia_coins': Decimal('0.00'),
            'is_free': True,
            'execution_type': 'langflow_node',
            'langflow_node_id': 'sentiment_analyzer_v1',
            'config_schema': {
                'language': {'type': 'string', 'default': 'ru', 'enum': ['ru', 'en', 'es', 'fr', 'de']},
                'detail_level': {'type': 'string', 'default': 'standard', 'enum': ['basic', 'standard', 'detailed']},
                'include_emotions': {'type': 'boolean', 'default': True},
                'confidence_threshold': {'type': 'number', 'default': 0.7, 'minimum': 0.1, 'maximum': 1.0}
            },
            'requirements': [],
            'capabilities': ['sentiment_analysis', 'emotion_detection', 'mood_tracking'],
            'status': 'active',
            'is_public': True
        },
        {
            'name': 'Генератор изображений DALL-E',
            'description': 'Создание уникальных изображений по текстовому описанию с использованием продвинутых AI моделей.',
            'version': '2.0.0',
            'creator': dev_users[3],
            'category': categories['Творчество'],
            'tags': ['image', 'generation', 'ai', 'dall-e', 'creative', 'art'],
            'price_ia_coins': Decimal('35.00'),
            'execution_type': 'api_call',
            'api_endpoint': 'https://api.openai.com/v1/images/generations',
            'config_schema': {
                'size': {'type': 'string', 'default': '1024x1024', 'enum': ['256x256', '512x512', '1024x1024']},
                'quality': {'type': 'string', 'default': 'standard', 'enum': ['standard', 'hd']},
                'style': {'type': 'string', 'default': 'vivid', 'enum': ['vivid', 'natural']},
                'n': {'type': 'integer', 'default': 1, 'minimum': 1, 'maximum': 4}
            },
            'requirements': ['OpenAI API ключ', 'DALL-E 3 доступ'],
            'capabilities': ['image_generation', 'creative_ai', 'prompt_optimization'],
            'status': 'active',
            'is_public': True
        },
        {
            'name': 'Планировщик задач',
            'description': 'Умный планировщик для управления задачами, напоминаниями и расписанием с интеграцией календарей.',
            'version': '1.8.3',
            'creator': dev_users[0],
            'category': categories['Утилиты'],
            'tags': ['planning', 'tasks', 'schedule', 'productivity', 'calendar'],
            'price_ia_coins': Decimal('12.00'),
            'execution_type': 'webhook',
            'webhook_url': 'https://taskplanner.zerobot.ai/webhook',
            'config_schema': {
                'timezone': {'type': 'string', 'default': 'Europe/Moscow'},
                'reminder_advance': {'type': 'integer', 'default': 15, 'minimum': 5, 'maximum': 1440},
                'calendar_integration': {'type': 'boolean', 'default': False},
                'priority_system': {'type': 'string', 'default': 'high_medium_low', 'enum': ['simple', 'high_medium_low', 'numeric']}
            },
            'requirements': ['Webhook endpoint'],
            'capabilities': ['task_management', 'scheduling', 'reminders', 'calendar_sync'],
            'status': 'active',
            'is_public': True
        },
        {
            'name': 'Криптовалютный трекер',
            'description': 'Отслеживание курсов криптовалют, анализ трендов и уведомления о важных изменениях цен.',
            'version': '2.2.1',
            'creator': dev_users[3],
            'category': categories['Бизнес'],
            'tags': ['crypto', 'trading', 'analysis', 'alerts', 'portfolio'],
            'price_ia_coins': Decimal('22.00'),
            'execution_type': 'api_call',
            'api_endpoint': 'https://api.cryptotracker.pro/v2/track',
            'config_schema': {
                'currencies': {'type': 'array', 'default': ['BTC', 'ETH', 'TON'], 'items': {'type': 'string'}},
                'alert_threshold': {'type': 'number', 'default': 5.0, 'minimum': 0.1, 'maximum': 50.0},
                'update_interval': {'type': 'integer', 'default': 300, 'minimum': 60, 'maximum': 3600},
                'include_analysis': {'type': 'boolean', 'default': True}
            },
            'requirements': ['CryptoTracker Pro API'],
            'capabilities': ['price_tracking', 'trend_analysis', 'portfolio_management', 'alerts'],
            'status': 'active',
            'is_public': True
        },
        {
            'name': 'Веб-скрапер Pro',
            'description': 'Профессиональный инструмент для извлечения данных с веб-сайтов с поддержкой JavaScript и анти-бот защиты.',
            'version': '1.3.0',
            'creator': dev_users[2],
            'category': categories['Утилиты'],
            'tags': ['scraping', 'web', 'data', 'extraction', 'automation'],
            'price_ia_coins': Decimal('28.00'),
            'execution_type': 'api_call',
            'api_endpoint': 'https://api.webscraper-pro.com/v1/scrape',
            'config_schema': {
                'javascript_enabled': {'type': 'boolean', 'default': True},
                'wait_time': {'type': 'integer', 'default': 3, 'minimum': 1, 'maximum': 30},
                'user_agent': {'type': 'string', 'default': 'chrome'},
                'proxy_enabled': {'type': 'boolean', 'default': False},
                'output_format': {'type': 'string', 'default': 'json', 'enum': ['json', 'csv', 'xml']}
            },
            'requirements': ['WebScraper Pro API', 'Proxy service (опционально)'],
            'capabilities': ['web_scraping', 'data_extraction', 'javascript_rendering', 'anti_bot_bypass'],
            'status': 'pending_review',
            'is_public': False
        }
    ]
    
    skills = []
    for skill_data in skills_data:
        skill, created = Skill.objects.get_or_create(
            name=skill_data['name'],
            creator=skill_data['creator'],
            defaults=skill_data
        )
        skills.append(skill)
        if created:
            print(f"✅ Создан навык: {skill.name} ({skill.category.icon})")
    
    # 4. Создание тестовых ботов (пропускаем из-за зависимости от personalities)
    print("\n🤖 Создание тестовых ботов...")
    print("ℹ️ Пропускаем создание ботов (требуется personalities app)")
    bots = []
    
    # 5. Создание оценок навыков
    print("\n⭐ Создание оценок навыков...")
    
    # Добавляем реалистичные оценки
    ratings_data = [
        (skills[0], test_user, 5, "Отличный навык! Генерирует качественный код."),
        (skills[0], admin_user, 4, "Хорошо работает, но иногда нужны правки."),
        (skills[1], test_user, 5, "Лучший переводчик! Очень точные переводы."),
        (skills[1], admin_user, 5, "Профессиональное качество перевода."),
        (skills[2], test_user, 4, "Точно определяет настроение, полезно."),
        (skills[3], admin_user, 5, "Потрясающие изображения! Очень креативно."),
        (skills[4], test_user, 4, "Удобный планировщик, помогает организоваться."),
        (skills[5], admin_user, 4, "Хорошо отслеживает криптовалюты."),
    ]
    
    for skill, user, rating, review in ratings_data:
        rating_obj, created = SkillRating.objects.get_or_create(
            skill=skill,
            user=user,
            defaults={
                'rating': rating,
                'review': review
            }
        )
        if created:
            print(f"✅ Создана оценка: {skill.name} - {rating}⭐")
    
    # 6. Обновление статистики навыков
    print("\n📊 Обновление статистики навыков...")
    
    # Добавляем реалистичную статистику
    stats_updates = [
        (skills[0], 156, Decimal('3900.00')),  # Python генератор
        (skills[1], 342, Decimal('6156.00')),  # Переводчик
        (skills[2], 89, Decimal('0.00')),      # Анализатор (бесплатный)
        (skills[3], 78, Decimal('2730.00')),   # DALL-E
        (skills[4], 234, Decimal('2808.00')),  # Планировщик
        (skills[5], 123, Decimal('2706.00')),  # Крипто трекер
    ]
    
    for skill, installations, revenue in stats_updates:
        skill.total_installations = installations
        skill.total_revenue = revenue
        skill.update_average_rating()
        skill.save()
        print(f"✅ Обновлена статистика: {skill.name} ({installations} установок)")
    
    print("\n🎉 Демонстрационные данные созданы успешно!")
    print("\n📋 Сводка:")
    print(f"👥 Пользователи: {User.objects.count()}")
    print(f"📂 Категории: {SkillCategory.objects.count()}")
    print(f"🧠 Навыки: {Skill.objects.count()}")
    print(f"🤖 Боты: {BotPassport.objects.count()} (создайте через админку)")
    print(f"⭐ Оценки: {SkillRating.objects.count()}")
    print()
    print("🔐 Учетные данные для входа:")
    print("   Админ: admin / admin123")
    print("   Тестовый пользователь: testuser / test123")
    print("   Разработчики: ai_developer, linguist_pro, code_master, data_scientist / dev123")
    print()
    print("🌐 Django Admin: http://localhost:8000/admin/")
    print("📱 IA-Mother Bot: @IAMotherBot в Telegram")

if __name__ == "__main__":
    create_demo_data()