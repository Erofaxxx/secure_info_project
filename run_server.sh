#!/bin/bash
# Скрипт запуска сервера SecureChat

echo "🚀 Запуск сервера SecureChat..."

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 не найден. Установите Python 3.8 или выше."
    exit 1
fi

# Проверка зависимостей
if ! python3 -c "import customtkinter" &> /dev/null; then
    echo "📦 Установка зависимостей..."
    pip3 install -r requirements.txt
fi

# Запуск сервера
python3 server.py
