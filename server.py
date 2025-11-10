#!/usr/bin/env python3
"""
Сервер мессенджера с E2E шифрованием
Обрабатывает регистрацию, авторизацию и пересылку зашифрованных сообщений
"""

import socket
import threading
import json
import sqlite3
import bcrypt
import logging
from datetime import datetime
from typing import Dict, Optional

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MessengerServer:
    def __init__(self, host: str = '0.0.0.0', port: int = 5555):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients: Dict[str, socket.socket] = {}  # username: socket
        self.clients_lock = threading.Lock()

        # Инициализация базы данных
        self.init_database()

    def init_database(self):
        """Создание таблиц базы данных"""
        conn = sqlite3.connect('messenger.db')
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                public_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица сообщений
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                receiver TEXT NOT NULL,
                encrypted_message TEXT NOT NULL,
                encrypted_key TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender) REFERENCES users(username),
                FOREIGN KEY (receiver) REFERENCES users(username)
            )
        ''')

        conn.commit()
        conn.close()
        logger.info("База данных инициализирована")

    def hash_password(self, password: str) -> str:
        """Хеширование пароля с bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def verify_password(self, password: str, hashed: str) -> bool:
        """Проверка пароля"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    def register_user(self, username: str, password: str, public_key: str) -> tuple:
        """Регистрация нового пользователя"""
        try:
            conn = sqlite3.connect('messenger.db')
            cursor = conn.cursor()

            # Проверка существования пользователя
            cursor.execute('SELECT username FROM users WHERE username = ?', (username,))
            if cursor.fetchone():
                conn.close()
                return False, "Пользователь уже существует"

            # Создание пользователя
            password_hash = self.hash_password(password)
            cursor.execute(
                'INSERT INTO users (username, password_hash, public_key) VALUES (?, ?, ?)',
                (username, password_hash, public_key)
            )
            conn.commit()
            conn.close()

            logger.info(f"Зарегистрирован новый пользователь: {username}")
            return True, "Регистрация успешна"

        except Exception as e:
            logger.error(f"Ошибка регистрации: {e}")
            return False, f"Ошибка: {str(e)}"

    def login_user(self, username: str, password: str) -> tuple:
        """Авторизация пользователя"""
        try:
            conn = sqlite3.connect('messenger.db')
            cursor = conn.cursor()

            cursor.execute('SELECT password_hash FROM users WHERE username = ?', (username,))
            result = cursor.fetchone()
            conn.close()

            if not result:
                return False, "Пользователь не найден"

            if self.verify_password(password, result[0]):
                logger.info(f"Пользователь {username} вошел в систему")
                return True, "Вход выполнен"
            else:
                return False, "Неверный пароль"

        except Exception as e:
            logger.error(f"Ошибка входа: {e}")
            return False, f"Ошибка: {str(e)}"

    def get_users(self, current_user: str) -> list:
        """Получить список всех пользователей кроме текущего"""
        try:
            conn = sqlite3.connect('messenger.db')
            cursor = conn.cursor()

            cursor.execute('SELECT username FROM users WHERE username != ?', (current_user,))
            users = [row[0] for row in cursor.fetchall()]
            conn.close()

            return users
        except Exception as e:
            logger.error(f"Ошибка получения пользователей: {e}")
            return []

    def get_public_key(self, username: str) -> Optional[str]:
        """Получить публичный ключ пользователя"""
        try:
            conn = sqlite3.connect('messenger.db')
            cursor = conn.cursor()

            cursor.execute('SELECT public_key FROM users WHERE username = ?', (username,))
            result = cursor.fetchone()
            conn.close()

            return result[0] if result else None
        except Exception as e:
            logger.error(f"Ошибка получения ключа: {e}")
            return None

    def save_message(self, sender: str, receiver: str, encrypted_message: str, encrypted_key: str) -> bool:
        """Сохранить зашифрованное сообщение"""
        try:
            conn = sqlite3.connect('messenger.db')
            cursor = conn.cursor()

            cursor.execute(
                'INSERT INTO messages (sender, receiver, encrypted_message, encrypted_key) VALUES (?, ?, ?, ?)',
                (sender, receiver, encrypted_message, encrypted_key)
            )
            conn.commit()
            conn.close()

            logger.info(f"Сообщение от {sender} к {receiver} сохранено")
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения сообщения: {e}")
            return False

    def get_messages(self, user1: str, user2: str) -> list:
        """Получить все сообщения между двумя пользователями"""
        try:
            conn = sqlite3.connect('messenger.db')
            cursor = conn.cursor()

            cursor.execute('''
                SELECT sender, receiver, encrypted_message, encrypted_key, timestamp
                FROM messages
                WHERE (sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?)
                ORDER BY timestamp ASC
            ''', (user1, user2, user2, user1))

            messages = []
            for row in cursor.fetchall():
                messages.append({
                    'sender': row[0],
                    'receiver': row[1],
                    'encrypted_message': row[2],
                    'encrypted_key': row[3],
                    'timestamp': row[4]
                })

            conn.close()
            return messages
        except Exception as e:
            logger.error(f"Ошибка получения сообщений: {e}")
            return []

    def handle_client(self, client_socket: socket.socket, address: tuple):
        """Обработка клиентского подключения"""
        logger.info(f"Новое подключение от {address}")
        current_user = None

        try:
            while True:
                # Получение данных от клиента
                data = client_socket.recv(4096).decode('utf-8')
                if not data:
                    break

                request = json.loads(data)
                command = request.get('command')

                response = {}

                if command == 'REGISTER':
                    success, message = self.register_user(
                        request['username'],
                        request['password'],
                        request['public_key']
                    )
                    response = {'success': success, 'message': message}

                elif command == 'LOGIN':
                    success, message = self.login_user(
                        request['username'],
                        request['password']
                    )
                    if success:
                        current_user = request['username']
                        with self.clients_lock:
                            self.clients[current_user] = client_socket
                    response = {'success': success, 'message': message}

                elif command == 'GET_USERS':
                    users = self.get_users(request['username'])
                    response = {'success': True, 'users': users}

                elif command == 'GET_PUBLIC_KEY':
                    public_key = self.get_public_key(request['username'])
                    response = {
                        'success': public_key is not None,
                        'public_key': public_key
                    }

                elif command == 'SEND_MESSAGE':
                    success = self.save_message(
                        request['sender'],
                        request['receiver'],
                        request['encrypted_message'],
                        request['encrypted_key']
                    )
                    response = {'success': success}

                    # Уведомить получателя если он онлайн
                    with self.clients_lock:
                        if request['receiver'] in self.clients:
                            try:
                                notification = json.dumps({
                                    'type': 'NEW_MESSAGE',
                                    'sender': request['sender']
                                })
                                self.clients[request['receiver']].send(notification.encode('utf-8'))
                            except:
                                pass

                elif command == 'GET_MESSAGES':
                    messages = self.get_messages(
                        request['user1'],
                        request['user2']
                    )
                    response = {'success': True, 'messages': messages}

                # Отправка ответа
                client_socket.send(json.dumps(response).encode('utf-8'))

        except Exception as e:
            logger.error(f"Ошибка обработки клиента {address}: {e}")
        finally:
            if current_user:
                with self.clients_lock:
                    if current_user in self.clients:
                        del self.clients[current_user]
                logger.info(f"Пользователь {current_user} отключился")
            client_socket.close()

    def start(self):
        """Запуск сервера"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)

        logger.info(f"Сервер запущен на {self.host}:{self.port}")
        print(f"🚀 Сервер мессенджера запущен на {self.host}:{self.port}")
        print("Ожидание подключений...")

        try:
            while True:
                client_socket, address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
        except KeyboardInterrupt:
            logger.info("Сервер остановлен пользователем")
            print("\n⏹️  Сервер остановлен")
        finally:
            self.server_socket.close()


if __name__ == '__main__':
    # Создание и запуск сервера
    server = MessengerServer(host='0.0.0.0', port=5555)
    server.start()
