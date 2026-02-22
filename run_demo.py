#!/usr/bin/env python3
"""
Демонстрационный скрипт для запуска Zero Bot Skills System
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def run_command(cmd, description, background=False):
    """Запуск команды с описанием"""
    print(f"🔄 {description}...")
    try:
        if background:
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return process
        else:
            result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
            print(f"✅ {description} - готово")
            return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при {description.lower()}: {e}")
        if e.stdout:
            print(f"Вывод: {e.stdout}")
        if e.stderr:
            print(f"Ошибки: {e.stderr}")
        return None

def main():
    """Основная функция демонстрации"""
    print("🚀 Zero Bot Skills System - Демонстрация")
    print("=" * 50)
    
    # Проверяем, что мы в правильной директории
    if not Path("manage.py").exists():
        print("❌ Файл manage.py не найден. Запустите скрипт из корня проекта.")
        return
    
    # 1. Применяем миграции
    print("\n1️⃣ Настройка базы данных")
    run_command("python manage.py migrate", "Применение миграций")
    
    # 2. Создаем демонстрационные данные
    print("\n2️⃣ Создание демонстрационных данных")
    run_command("python create_demo_skills.py", "Создание навыков и пользователей")
    
    # 3. Собираем статические файлы
    print("\n3️⃣ Подготовка статических файлов")
    run_command("python manage.py collectstatic --noinput", "Сбор статических файлов")
    
    print("\n🎯 Система готова к демонстрации!")
    print("\n📋 Доступные интерфейсы:")
    print("   🌐 Django Admin: http://localhost:8000/admin/")
    print("   📊 API Root: http://localhost:8000/api/v1/")
    print("   🧠 Skills API: http://localhost:8000/api/v1/skills/")
    print("   📱 IA-Mother Bot: @IAMotherBot в Telegram")
    
    print("\n🔐 Учетные данные:")
    print("   👨‍💼 Админ: admin / admin123")
    print("   🧪 Тестовый: testuser / test123")
    
    print("\n🚀 Запуск Django сервера...")
    print("   Остановка: Ctrl+C")
    print("=" * 50)
    
    # 4. Запускаем Django сервер
    try:
        subprocess.run("python manage.py runserver 0.0.0.0:8000", shell=True, check=True)
    except KeyboardInterrupt:
        print("\n🛑 Сервер остановлен")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка запуска сервера: {e}")

if __name__ == "__main__":
    main()