#!/usr/bin/env python3
"""
Скрипт для очистки старых сообщений из базы данных
Используется для удаления сообщений, зашифрованных старыми ключами
"""

import sqlite3
import sys
from datetime import datetime

def clear_old_messages(db_path='server_data.db'):
    """Очищает все сообщения из базы данных"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Подсчитываем сколько сообщений будет удалено
        cursor.execute('SELECT COUNT(*) FROM messages')
        count = cursor.fetchone()[0]

        if count == 0:
            print("✅ База данных уже пустая, сообщений нет")
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
    db_path = sys.argv[1] if len(sys.argv) > 1 else 'server_data.db'

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
