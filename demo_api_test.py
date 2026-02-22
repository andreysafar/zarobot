#!/usr/bin/env python3
"""
Демонстрация работы API навыков
"""

import asyncio
import json
import httpx
from typing import Dict, List

CORE_API_URL = "http://localhost:8000"

async def test_api():
    """Тестирование API навыков"""
    print("🚀 Тестирование Zero Bot Skills API")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        
        # 1. Проверка health endpoint
        print("\n1️⃣ Проверка Health Endpoint")
        try:
            response = await client.get(f"{CORE_API_URL}/health/")
            if response.status_code == 200:
                print(f"✅ Health: {response.json()}")
            else:
                print(f"❌ Health Error: {response.status_code}")
        except Exception as e:
            print(f"❌ Health Error: {e}")
        
        # 2. Получение категорий
        print("\n2️⃣ Категории навыков")
        try:
            response = await client.get(f"{CORE_API_URL}/api/v1/skills/categories/")
            if response.status_code == 200:
                categories = response.json()['results']
                print(f"✅ Найдено {len(categories)} категорий:")
                for cat in categories:
                    print(f"   {cat['icon']} {cat['name']} ({cat['skills_count']} навыков)")
            else:
                print(f"❌ Categories Error: {response.status_code}")
        except Exception as e:
            print(f"❌ Categories Error: {e}")
        
        # 3. Получение навыков
        print("\n3️⃣ Навыки")
        try:
            response = await client.get(f"{CORE_API_URL}/api/v1/skills/skills/")
            if response.status_code == 200:
                skills = response.json()['results']
                print(f"✅ Найдено {len(skills)} навыков:")
                for skill in skills[:3]:  # Показываем первые 3
                    print(f"   🧠 {skill['name']} v{skill['version']}")
                    print(f"      💰 {skill['price_ia_coins']} IA-Coins | ⭐ {skill['average_rating']}/5")
                    print(f"      📊 {skill['total_installations']} установок")
                    print(f"      🏷️ {skill['category_name']} {skill.get('category_icon', '')}")
                    print()
            else:
                print(f"❌ Skills Error: {response.status_code}")
        except Exception as e:
            print(f"❌ Skills Error: {e}")
        
        # 4. Поиск навыков
        print("\n4️⃣ Поиск навыков (по слову 'код')")
        try:
            response = await client.get(f"{CORE_API_URL}/api/v1/skills/skills/?search=код")
            if response.status_code == 200:
                skills = response.json()['results']
                print(f"✅ Найдено {len(skills)} навыков по поиску:")
                for skill in skills:
                    print(f"   🔍 {skill['name']} - {skill['description'][:50]}...")
            else:
                print(f"❌ Search Error: {response.status_code}")
        except Exception as e:
            print(f"❌ Search Error: {e}")
        
        # 5. Фильтрация по категории
        print("\n5️⃣ Фильтрация по категории 'Разработка'")
        try:
            response = await client.get(f"{CORE_API_URL}/api/v1/skills/skills/?category=1")
            if response.status_code == 200:
                skills = response.json()['results']
                print(f"✅ Найдено {len(skills)} навыков в категории 'Разработка':")
                for skill in skills:
                    print(f"   💻 {skill['name']} - {skill['price_ia_coins']} IA-Coins")
            else:
                print(f"❌ Filter Error: {response.status_code}")
        except Exception as e:
            print(f"❌ Filter Error: {e}")
        
        # 6. Популярные навыки
        print("\n6️⃣ Популярные навыки")
        try:
            response = await client.post(f"{CORE_API_URL}/api/v1/skills/skills/featured/", json={})
            if response.status_code == 200:
                skills = response.json()['results']
                print(f"✅ Найдено {len(skills)} популярных навыков:")
                for skill in skills[:3]:
                    print(f"   🔥 {skill['name']} (популярность: {skill['popularity_score']})")
            else:
                print(f"❌ Featured Error: {response.status_code}")
        except Exception as e:
            print(f"❌ Featured Error: {e}")

def print_demo_info():
    """Информация о демонстрации"""
    print("\n" + "=" * 50)
    print("🎯 ДЕМОНСТРАЦИЯ ГОТОВА!")
    print("=" * 50)
    print(f"🌐 Core API: {CORE_API_URL}")
    print(f"📊 Admin Panel: {CORE_API_URL}/admin/")
    print(f"🧠 Skills API: {CORE_API_URL}/api/v1/skills/")
    print()
    print("📱 Доступные эндпоинты:")
    print("   • GET /api/v1/skills/categories/ - Категории навыков")
    print("   • GET /api/v1/skills/skills/ - Список навыков")
    print("   • GET /api/v1/skills/skills/?search=term - Поиск навыков")
    print("   • GET /api/v1/skills/skills/?category=1 - Фильтр по категории")
    print("   • POST /api/v1/skills/skills/featured/ - Популярные навыки")
    print()
    print("🔑 Данные для входа в админку:")
    print("   • Username: admin")
    print("   • Password: admin123")
    print()
    print("💡 Для тестирования Telegram бота нужно:")
    print("   1. Получить API ID/Hash на https://my.telegram.org")
    print("   2. Настроить webhook для продакшена")
    print("   3. Или использовать polling режим для разработки")

if __name__ == "__main__":
    asyncio.run(test_api())
    print_demo_info()