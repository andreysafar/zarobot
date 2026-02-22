#!/bin/bash

echo "🚀 Запускаю Zero Bot Platform локально..."
echo ""

# Проверка зависимостей
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден"
    exit 1
fi

# Проверка переменных окружения
if [[ -z "$TELEGRAM_API_ID" || -z "$TELEGRAM_API_HASH" ]]; then
    echo "❌ Нужны переменные окружения:"
    echo "   export TELEGRAM_API_ID=25039464"
    echo "   export TELEGRAM_API_HASH=9ebe53a317b075a5eb7f8ea577f7f733"
    echo ""
    echo "Или создай файл .env с этими переменными"
    exit 1
fi

# Установка зависимостей если нужно
if [[ ! -d "venv" ]]; then
    echo "📦 Создаю виртуальное окружение..."
    python3 -m venv venv
fi

source venv/bin/activate

echo "📦 Устанавливаю зависимости..."
pip install -q telethon loguru

echo ""
echo "🤖 Доступные боты:"
echo "1. IA-Mother (Master Bot) — @IAMotherBot"
echo "2. Zero Bot (с личностью Ия) — @Safar_test_bot"
echo ""

# Меню выбора
echo "Выберите бота для запуска:"
echo "1) IA-Mother"
echo "2) Zero Bot" 
echo "3) Оба бота (в разных терминалах)"
echo ""
read -p "Ваш выбор (1-3): " choice

case $choice in
    1)
        echo "🚀 Запускаю IA-Mother..."
        python3 test_local.py
        ;;
    2)
        echo "🚀 Запускаю Zero Bot..."
        python3 test_zero_local.py
        ;;
    3)
        echo "🚀 Запускаю оба бота..."
        echo "IA-Mother запускается в фоне..."
        python3 test_local.py &
        IA_MOTHER_PID=$!
        
        echo "Zero Bot запускается..."
        python3 test_zero_local.py &
        ZERO_BOT_PID=$!
        
        echo ""
        echo "✅ Оба бота запущены!"
        echo "📱 IA-Mother: @IAMotherBot"
        echo "📱 Zero Bot: @Safar_test_bot"
        echo ""
        echo "🛑 Нажми Ctrl+C для остановки всех ботов"
        
        # Ожидание сигнала остановки
        trap "echo ''; echo '🛑 Останавливаю ботов...'; kill $IA_MOTHER_PID $ZERO_BOT_PID 2>/dev/null; exit 0" SIGINT
        wait
        ;;
    *)
        echo "❌ Неверный выбор"
        exit 1
        ;;
esac