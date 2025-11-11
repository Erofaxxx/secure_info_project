#!/usr/bin/env python3
"""
Скрипт для очистки старых сообщений из базы данных
Используется для удаления сообщений, зашифрованных старыми ключами
"""

import sqlite3
import sys
from datetime import datetime

def clear_old_messages(db_path='messenger.db'):
    """Очищает все сообщения из базы данных"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Проверяем существует ли таблица messages
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='messages'"
        )
        table_exists = cursor.fetchone() is not None

        if not table_exists:
            print("✅ Таблица messages не существует")
            print("✅ База данных чистая, старых сообщений нет")
            print("ℹ️  Таблица будет создана при первом запуске сервера")
            conn.close()
            return True

        # Подсчитываем сколько сообщений будет удалено
        cursor.execute('SELECT COUNT(*) FROM messages')
        count = cursor.fetchone()[0]

        if count == 0:
            print("✅ База данных уже пустая, сообщений нет")
            conn.close()
            return True

        print(f"⚠️  Найдено {count} сообщений")
        print("⚠️  Все сообщения будут удалены!")

        # Удаляем все сообщения
        cursor.execute('DELETE FROM messages')
        conn.commit()

        print(f"✅ Успешно удалено {count} сообщений")
        print("✅ Теперь все новые сообщения будут корректно расшифровываться")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Ошибка при очистке базы данных: {e}")
        return False

if __name__ == '__main__':
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'messenger.db'

    print("=" * 50)
    print("ОЧИСТКА СТАРЫХ СООБЩЕНИЙ")
    print("=" * 50)
    print(f"База данных: {db_path}")
    print()

    if clear_old_messages(db_path):
        print()
        print("🎉 Готово! Теперь:")
        print("   1. Перезапустите сервер")
        print("   2. Перезапустите оба клиента")
        print("   3. Все новые сообщения будут нормально расшифровываться")
    else:
        sys.exit(1)
