@echo off
REM Скрипт запуска клиента SecureChat для Windows

echo 💻 Запуск клиента SecureChat...

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден. Установите Python 3.8 или выше.
    pause
    exit /b 1
)

REM Проверка зависимостей
python -c "import customtkinter" >nul 2>&1
if errorlevel 1 (
    echo 📦 Установка зависимостей...
    pip install -r requirements.txt
)

REM Запуск клиента
python client.py
pause
