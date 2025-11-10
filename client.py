#!/usr/bin/env python3
"""
Клиент мессенджера с E2E шифрованием
Графический интерфейс на CustomTkinter
"""

import customtkinter as ctk
import socket
import json
import threading
from tkinter import messagebox
from datetime import datetime
from encryption import E2EEncryption
import os

# Настройка темы
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MessengerClient:
    def __init__(self, server_host: str = 'localhost', server_port: int = 5555):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.username = None
        self.encryption = E2EEncryption()
        self.encryption.generate_keys()
        self.current_chat = None
        self.public_keys_cache = {}  # username: public_key

        # GUI элементы
        self.root = None
        self.login_frame = None
        self.main_frame = None
        self.chat_list_frame = None
        self.message_frame = None
        self.chat_buttons = []

        # Данные
        self.users = []
        self.messages_cache = {}  # username: [messages]
        self.sent_messages_cache = {}  # (receiver, timestamp): plaintext - кэш своих сообщений

    def connect_to_server(self) -> bool:
        """Подключение к серверу"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            return True
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось подключиться к серверу:\n{e}")
            return False

    def reconnect(self) -> bool:
        """Переподключение к серверу"""
        try:
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            print("✅ Переподключение успешно")
            return True
        except Exception as e:
            print(f"❌ Не удалось переподключиться: {e}")
            return False

    def send_request(self, data: dict, retry_on_disconnect: bool = True) -> dict:
        """Отправка запроса на сервер и получение ответа

        Args:
            data: Данные для отправки
            retry_on_disconnect: Автоматически переподключаться при разрыве соединения
        """
        try:
            # Отправляем с разделителем \n
            message = json.dumps(data) + '\n'
            self.socket.send(message.encode('utf-8'))

            # Читаем до разделителя \n
            response_data = b''
            while True:
                chunk = self.socket.recv(1024)
                if not chunk:
                    raise ConnectionError("Соединение закрыто сервером")
                response_data += chunk
                if b'\n' in response_data:
                    # Нашли конец сообщения
                    break

            # Берем только первое сообщение (до \n)
            response_str = response_data.split(b'\n')[0].decode('utf-8')
            return json.loads(response_str)

        except (BrokenPipeError, ConnectionError, ConnectionResetError) as e:
            # Соединение разорвано - пробуем переподключиться
            if retry_on_disconnect:
                print(f"⚠️  Соединение разорвано ({e}), переподключаюсь...")
                if self.reconnect():
                    # Повторяем запрос БЕЗ повторного retry (чтобы не зациклиться)
                    return self.send_request(data, retry_on_disconnect=False)

            print(f"❌ Ошибка соединения: {e}")
            return {'success': False, 'message': f'Connection error: {str(e)}'}

        except json.JSONDecodeError as e:
            print(f"Ошибка JSON: {e}")
            return {'success': False, 'message': f'JSON error: {str(e)}'}

        except Exception as e:
            print(f"Ошибка отправки запроса: {e}")
            return {'success': False, 'message': str(e)}

    def register(self, username: str, password: str) -> tuple:
        """Регистрация нового пользователя"""
        data = {
            'command': 'REGISTER',
            'username': username,
            'password': password,
            'public_key': self.encryption.get_public_key_string()
        }
        response = self.send_request(data)
        return response['success'], response.get('message', '')

    def login(self, username: str, password: str) -> tuple:
        """Вход в систему"""
        data = {
            'command': 'LOGIN',
            'username': username,
            'password': password,
            'public_key': self.encryption.get_public_key_string()  # Обновляем ключ при логине!
        }
        response = self.send_request(data)
        if response['success']:
            self.username = username
            # ОТКЛЮЧЕНО: Поток конфликтует с send_request при использовании одного сокета
            # threading.Thread(target=self.listen_for_notifications, daemon=True).start()
        return response['success'], response.get('message', '')

    def get_users(self) -> list:
        """Получить список пользователей"""
        data = {
            'command': 'GET_USERS',
            'username': self.username
        }
        response = self.send_request(data)
        if response['success']:
            return response['users'][:5]  # Максимум 5 чатов
        return []

    def get_public_key(self, username: str) -> str:
        """Получить публичный ключ пользователя"""
        if username in self.public_keys_cache:
            return self.public_keys_cache[username]

        data = {
            'command': 'GET_PUBLIC_KEY',
            'username': username
        }
        response = self.send_request(data)
        if response['success']:
            self.public_keys_cache[username] = response['public_key']
            return response['public_key']
        return None

    def send_message(self, receiver: str, message: str) -> tuple:
        """Отправить зашифрованное сообщение, возвращает (success, timestamp)"""
        try:
            # Получаем публичный ключ получателя
            receiver_public_key = self.get_public_key(receiver)
            if not receiver_public_key:
                return False, None

            # Шифруем сообщение
            encrypted_message, encrypted_key = self.encryption.encrypt_message(
                message,
                receiver_public_key
            )

            # Отправляем на сервер
            data = {
                'command': 'SEND_MESSAGE',
                'sender': self.username,
                'receiver': receiver,
                'encrypted_message': encrypted_message,
                'encrypted_key': encrypted_key
            }
            response = self.send_request(data)

            if response['success']:
                # Сохраняем в кэш с timestamp от сервера
                timestamp = response.get('timestamp')
                if timestamp:
                    cache_key = (receiver, timestamp)
                    self.sent_messages_cache[cache_key] = message
                    print(f"  💾 Сохранено в кэш: {cache_key} = {message[:30]}...")
                return True, timestamp
            return False, None
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")
            return False, None

    def get_messages(self, other_user: str) -> list:
        """Получить сообщения с другим пользователем"""
        data = {
            'command': 'GET_MESSAGES',
            'user1': self.username,
            'user2': other_user
        }
        response = self.send_request(data)
        if response['success']:
            # Дешифруем сообщения
            decrypted_messages = []
            print(f"\n=== Обработка {len(response['messages'])} сообщений ===")
            for idx, msg in enumerate(response['messages']):
                try:
                    print(f"\nСообщение {idx+1}:")
                    print(f"  От: {msg['sender']} → Кому: {msg['receiver']}")
                    print(f"  Timestamp: {msg['timestamp']}")
                    print(f"  Я: {self.username}")

                    # Дешифруем только входящие сообщения
                    if msg['receiver'] == self.username:
                        print(f"  → Тип: ВХОДЯЩЕЕ (расшифровываю)")
                        # Входящее - расшифровываем своим приватным ключом
                        text = self.encryption.decrypt_message(
                            msg['encrypted_message'],
                            msg['encrypted_key']
                        )
                        print(f"  ✅ Расшифровано: {text[:50]}...")
                    else:
                        print(f"  → Тип: ИСХОДЯЩЕЕ (проверяю кэш)")
                        # Исходящее - НЕ МОЖЕМ расшифровать (зашифровано для получателя)
                        # Проверяем кэш отправленных сообщений
                        cache_key = (msg['receiver'], msg['timestamp'])
                        print(f"  Ключ кэша: {cache_key}")
                        print(f"  Кэш содержит: {list(self.sent_messages_cache.keys())}")
                        if cache_key in self.sent_messages_cache:
                            text = self.sent_messages_cache[cache_key]
                            print(f"  ✅ Найдено в кэше: {text[:50]}...")
                        else:
                            # Если нет в кэше (старое сообщение или после перезапуска)
                            text = "[Моё сообщение - зашифровано]"
                            print(f"  ⚠️  НЕ найдено в кэше")

                    decrypted_messages.append({
                        'sender': msg['sender'],
                        'text': text,
                        'timestamp': msg['timestamp']
                    })
                except Exception as e:
                    print(f"  ❌ Ошибка дешифровки: {e}")
                    import traceback
                    traceback.print_exc()
                    decrypted_messages.append({
                        'sender': msg['sender'],
                        'text': '[Ошибка дешифровки]',
                        'timestamp': msg['timestamp']
                    })
            return decrypted_messages
        return []

    def listen_for_notifications(self):
        """Прослушивание уведомлений от сервера"""
        try:
            while True:
                data = self.socket.recv(4096).decode('utf-8')
                if data:
                    notification = json.loads(data)
                    if notification['type'] == 'NEW_MESSAGE':
                        # Обновить чат если он открыт
                        if self.current_chat == notification['sender']:
                            self.root.after(0, self.load_chat, notification['sender'])
        except:
            pass

    # ================== GUI ==================

    def create_gui(self):
        """Создание графического интерфейса"""
        self.root = ctk.CTk()
        self.root.title("SecureChat - E2E Encrypted Messenger")
        self.root.geometry("400x500")

        # Показываем экран входа
        self.show_login_screen()

        self.root.mainloop()

    def show_login_screen(self):
        """Экран входа/регистрации"""
        if self.main_frame:
            self.main_frame.destroy()

        self.login_frame = ctk.CTkFrame(self.root)
        self.login_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Заголовок
        title = ctk.CTkLabel(
            self.login_frame,
            text="🔒 SecureChat",
            font=("Helvetica", 28, "bold")
        )
        title.pack(pady=(20, 10))

        subtitle = ctk.CTkLabel(
            self.login_frame,
            text="End-to-End Encrypted Messenger",
            font=("Helvetica", 12),
            text_color="gray"
        )
        subtitle.pack(pady=(0, 30))

        # Поле username
        username_label = ctk.CTkLabel(
            self.login_frame,
            text="Имя пользователя:",
            font=("Helvetica", 14)
        )
        username_label.pack(pady=(10, 5))

        self.username_entry = ctk.CTkEntry(
            self.login_frame,
            width=300,
            height=40,
            placeholder_text="Введите username"
        )
        self.username_entry.pack(pady=(0, 15))

        # Поле пароля
        password_label = ctk.CTkLabel(
            self.login_frame,
            text="Пароль:",
            font=("Helvetica", 14)
        )
        password_label.pack(pady=(10, 5))

        self.password_entry = ctk.CTkEntry(
            self.login_frame,
            width=300,
            height=40,
            placeholder_text="Введите пароль",
            show="•"
        )
        self.password_entry.pack(pady=(0, 25))

        # Кнопки
        login_button = ctk.CTkButton(
            self.login_frame,
            text="Войти",
            width=300,
            height=40,
            font=("Helvetica", 14, "bold"),
            command=self.handle_login
        )
        login_button.pack(pady=5)

        register_button = ctk.CTkButton(
            self.login_frame,
            text="Регистрация",
            width=300,
            height=40,
            font=("Helvetica", 14),
            fg_color="transparent",
            border_width=2,
            command=self.handle_register
        )
        register_button.pack(pady=5)

        # Информация о сервере
        server_info = ctk.CTkLabel(
            self.login_frame,
            text=f"Сервер: {self.server_host}:{self.server_port}",
            font=("Helvetica", 10),
            text_color="gray"
        )
        server_info.pack(side="bottom", pady=10)

    def handle_login(self):
        """Обработка входа"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showwarning("Внимание", "Заполните все поля")
            return

        if not self.socket:
            if not self.connect_to_server():
                return

        success, message = self.login(username, password)
        if success:
            self.login_frame.destroy()
            self.show_main_screen()
        else:
            messagebox.showerror("Ошибка", message)

    def handle_register(self):
        """Обработка регистрации"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showwarning("Внимание", "Заполните все поля")
            return

        if len(password) < 4:
            messagebox.showwarning("Внимание", "Пароль должен быть минимум 4 символа")
            return

        if not self.socket:
            if not self.connect_to_server():
                return

        success, message = self.register(username, password)
        if success:
            messagebox.showinfo("Успех", "Регистрация успешна! Теперь войдите в систему.")
        else:
            messagebox.showerror("Ошибка", message)

    def show_main_screen(self):
        """Главный экран мессенджера"""
        self.root.geometry("900x600")
        self.root.title(f"SecureChat - {self.username}")

        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        # Левая панель - список чатов
        left_panel = ctk.CTkFrame(self.main_frame, width=250, corner_radius=0)
        left_panel.pack(side="left", fill="y")
        left_panel.pack_propagate(False)

        # Заголовок списка чатов
        chats_header = ctk.CTkFrame(left_panel, fg_color="#1a1a1a", corner_radius=0)
        chats_header.pack(fill="x", pady=0)

        chats_title = ctk.CTkLabel(
            chats_header,
            text="Чаты",
            font=("Helvetica", 18, "bold"),
            anchor="w"
        )
        chats_title.pack(padx=15, pady=15)

        # Список чатов
        self.chat_list_frame = ctk.CTkScrollableFrame(
            left_panel,
            fg_color="transparent"
        )
        self.chat_list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Правая панель - чат
        right_panel = ctk.CTkFrame(self.main_frame, corner_radius=0)
        right_panel.pack(side="right", fill="both", expand=True)

        # Заголовок чата
        self.chat_header = ctk.CTkFrame(right_panel, fg_color="#1a1a1a", height=60, corner_radius=0)
        self.chat_header.pack(fill="x")
        self.chat_header.pack_propagate(False)

        # Левая часть - имя чата
        self.chat_title = ctk.CTkLabel(
            self.chat_header,
            text="Выберите чат",
            font=("Helvetica", 16, "bold"),
            anchor="w"
        )
        self.chat_title.pack(side="left", padx=20, pady=15)

        # Правая часть - кнопка обновить
        self.refresh_button = ctk.CTkButton(
            self.chat_header,
            text="🔄 Обновить",
            width=100,
            height=35,
            font=("Helvetica", 12),
            command=self.refresh_current_chat
        )
        self.refresh_button.pack(side="right", padx=20, pady=12)

        # Область сообщений
        self.message_frame = ctk.CTkScrollableFrame(
            right_panel,
            fg_color="#2b2b2b"
        )
        self.message_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Поле ввода
        input_frame = ctk.CTkFrame(right_panel, fg_color="transparent", height=70)
        input_frame.pack(fill="x", padx=10, pady=(0, 10))
        input_frame.pack_propagate(False)

        self.message_input = ctk.CTkEntry(
            input_frame,
            placeholder_text="Введите сообщение...",
            height=50,
            font=("Helvetica", 13)
        )
        self.message_input.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.message_input.bind("<Return>", lambda e: self.send_message_gui())

        send_button = ctk.CTkButton(
            input_frame,
            text="Отправить",
            width=100,
            height=50,
            font=("Helvetica", 13, "bold"),
            command=self.send_message_gui
        )
        send_button.pack(side="right")

        # Загружаем список пользователей
        self.load_users()

    def load_users(self):
        """Загрузка списка пользователей (чатов)"""
        self.users = self.get_users()

        # Очищаем старый список
        for btn in self.chat_buttons:
            btn.destroy()
        self.chat_buttons = []

        # Создаем кнопки для каждого пользователя
        for user in self.users:
            btn = ctk.CTkButton(
                self.chat_list_frame,
                text=f"👤 {user}",
                height=50,
                font=("Helvetica", 14),
                anchor="w",
                fg_color="transparent",
                hover_color="#3a3a3a",
                command=lambda u=user: self.load_chat(u)
            )
            btn.pack(fill="x", pady=2)
            self.chat_buttons.append(btn)

    def load_chat(self, username: str):
        """Загрузка чата с пользователем"""
        self.current_chat = username
        self.chat_title.configure(text=f"👤 {username}")

        # Очищаем сообщения
        for widget in self.message_frame.winfo_children():
            widget.destroy()

        # Загружаем сообщения
        messages = self.get_messages(username)
        self.messages_cache[username] = messages

        for msg in messages:
            is_mine = msg['sender'] == self.username
            self.display_message(msg['text'], is_mine, msg['timestamp'])

        # Прокручиваем вниз
        self.root.update()
        self.message_frame._parent_canvas.yview_moveto(1.0)

    def refresh_current_chat(self):
        """Обновить текущий чат (загрузить новые сообщения)"""
        if self.current_chat:
            self.load_chat(self.current_chat)

    def display_message(self, text: str, is_mine: bool, timestamp: str = None):
        """Отображение сообщения в чате"""
        # Контейнер для сообщения
        msg_container = ctk.CTkFrame(
            self.message_frame,
            fg_color="transparent"
        )
        msg_container.pack(fill="x", pady=5)

        # Сообщение
        msg_frame = ctk.CTkFrame(
            msg_container,
            fg_color="#0084ff" if is_mine else "#3a3a3a",
            corner_radius=15
        )

        if is_mine:
            msg_frame.pack(side="right", padx=(50, 5))
        else:
            msg_frame.pack(side="left", padx=(5, 50))

        msg_label = ctk.CTkLabel(
            msg_frame,
            text=text,
            font=("Helvetica", 13),
            wraplength=400,
            justify="left",
            anchor="w"
        )
        msg_label.pack(padx=15, pady=10)

        # Время
        if timestamp:
            try:
                time_str = datetime.fromisoformat(timestamp).strftime("%H:%M")
            except:
                time_str = ""

            if time_str:
                time_label = ctk.CTkLabel(
                    msg_container,
                    text=time_str,
                    font=("Helvetica", 9),
                    text_color="gray"
                )
                if is_mine:
                    time_label.pack(side="right", padx=10)
                else:
                    time_label.pack(side="left", padx=10)

    def send_message_gui(self):
        """Отправка сообщения из GUI"""
        if not self.current_chat:
            messagebox.showwarning("Внимание", "Выберите чат")
            return

        text = self.message_input.get().strip()
        if not text:
            return

        # Отправляем
        success, timestamp = self.send_message(self.current_chat, text)
        if success:
            # Используем timestamp от сервера (если не получили - создаём локальный)
            if not timestamp:
                timestamp = datetime.now().isoformat()

            # Кэш уже обновлён в send_message(), просто отображаем сообщение
            self.display_message(text, True, timestamp)
            self.message_input.delete(0, 'end')

            # Прокручиваем вниз
            self.root.update()
            self.message_frame._parent_canvas.yview_moveto(1.0)
        else:
            messagebox.showerror("Ошибка", "Не удалось отправить сообщение")


def main():
    """Точка входа"""
    # Запрашиваем адрес сервера
    import sys

    if len(sys.argv) > 1:
        server_host = sys.argv[1]
    else:
        server_host = input("Введите адрес сервера (по умолчанию localhost): ").strip()
        if not server_host:
            server_host = 'localhost'

    client = MessengerClient(server_host=server_host, server_port=5555)
    client.create_gui()


if __name__ == '__main__':
    main()
