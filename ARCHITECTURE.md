# 🏗️ Архитектура SecureChat

Подробное описание архитектуры, протоколов и реализации E2E шифрования.

## 📊 Общая схема

```
┌──────────────────────────────────────────────────────────────┐
│                    CLIENT APPLICATION                         │
├──────────────────────────────────────────────────────────────┤
│  GUI Layer (CustomTkinter)                                   │
│  ├─ Login/Register Screen                                    │
│  ├─ Main Screen (Chat List + Message View)                   │
│  └─ Message Input                                            │
├──────────────────────────────────────────────────────────────┤
│  Business Logic                                              │
│  ├─ User Authentication                                      │
│  ├─ Message Sending/Receiving                                │
│  ├─ User List Management                                     │
│  └─ Notification Handling                                    │
├──────────────────────────────────────────────────────────────┤
│  Encryption Layer (encryption.py)                            │
│  ├─ RSA Key Generation (2048 bit)                            │
│  ├─ Message Encryption (Hybrid: RSA + AES)                   │
│  ├─ Message Decryption                                       │
│  └─ Key Management                                           │
├──────────────────────────────────────────────────────────────┤
│  Network Layer (socket)                                      │
│  ├─ TCP Connection to Server                                 │
│  ├─ JSON Protocol                                            │
│  └─ Request/Response Handling                                │
└──────────────────────────────────────────────────────────────┘
                            │
                            │ TCP/IP (Port 5555)
                            │ JSON Protocol
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                     SERVER APPLICATION                        │
├──────────────────────────────────────────────────────────────┤
│  Network Layer                                               │
│  ├─ TCP Server (Multi-threaded)                              │
│  ├─ Client Connection Management                             │
│  └─ JSON Protocol Parser                                     │
├──────────────────────────────────────────────────────────────┤
│  Business Logic                                              │
│  ├─ User Registration & Login                                │
│  ├─ Password Hashing (bcrypt)                                │
│  ├─ Message Routing                                          │
│  ├─ Public Key Management                                    │
│  └─ Online User Tracking                                     │
├──────────────────────────────────────────────────────────────┤
│  Data Layer (SQLite)                                         │
│  ├─ users table                                              │
│  │   ├─ id                                                   │
│  │   ├─ username                                             │
│  │   ├─ password_hash (bcrypt)                               │
│  │   ├─ public_key (PEM format)                              │
│  │   └─ created_at                                           │
│  └─ messages table                                           │
│      ├─ id                                                   │
│      ├─ sender                                               │
│      ├─ receiver                                             │
│      ├─ encrypted_message (base64)                           │
│      ├─ encrypted_key (base64)                               │
│      └─ timestamp                                            │
└──────────────────────────────────────────────────────────────┘
```

## 🔐 Детали E2E шифрования

### 1. Генерация ключей (при первом запуске клиента)

```python
# encryption.py: E2EEncryption.__init__()

# Генерация RSA ключей
private_key = rsa.generate_private_key(
    public_exponent=65537,  # Стандартное значение
    key_size=2048          # 2048 бит = 256 байт
)
public_key = private_key.public_key()

# Приватный ключ ОСТАЁТСЯ на клиенте
# Публичный ключ отправляется на сервер
```

**Почему RSA 2048 бит?**
- Достаточно для учебного проекта
- Баланс между безопасностью и скоростью
- Рекомендовано NIST до 2030 года

### 2. Процесс отправки сообщения

#### Шаг 1: Клиент получает публичный ключ получателя

```python
# client.py: get_public_key()

request = {
    'command': 'GET_PUBLIC_KEY',
    'username': 'bob'
}
# Отправка на сервер

response = {
    'success': True,
    'public_key': '-----BEGIN PUBLIC KEY-----\n...'
}
```

#### Шаг 2: Шифрование сообщения (Гибридная схема)

```python
# encryption.py: encrypt_message()

# 1. Генерируем случайный AES ключ для ЭТОГО сообщения
fernet_key = Fernet.generate_key()  # 32 байта (256 бит)

# 2. Шифруем сообщение симметричным ключом (БЫСТРО!)
fernet = Fernet(fernet_key)
encrypted_message = fernet.encrypt(message.encode('utf-8'))

# 3. Шифруем сам AES ключ публичным RSA ключом получателя (медленно, но ключ маленький)
encrypted_key = recipient_public_key.encrypt(
    fernet_key,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
)

# 4. Конвертируем в base64 для удобной передачи
return (
    base64.b64encode(encrypted_message).decode('utf-8'),
    base64.b64encode(encrypted_key).decode('utf-8')
)
```

**Почему гибридная схема?**
- RSA медленный для длинных сообщений
- AES очень быстрый, но требует общего ключа
- Решение: шифруем данные AES, а сам AES ключ шифруем RSA
- Каждое сообщение использует новый случайный AES ключ (Forward Secrecy)

#### Шаг 3: Отправка на сервер

```python
# client.py: send_message()

request = {
    'command': 'SEND_MESSAGE',
    'sender': 'alice',
    'receiver': 'bob',
    'encrypted_message': 'gAAAAA...',  # base64 AES-зашифрованное сообщение
    'encrypted_key': 'kfJ8s3...'       # base64 RSA-зашифрованный AES ключ
}
```

#### Шаг 4: Сервер сохраняет и пересылает

```python
# server.py: save_message()

# Сервер НЕ может расшифровать!
# Просто сохраняет в базу данных КАК ЕСТЬ
cursor.execute(
    'INSERT INTO messages (sender, receiver, encrypted_message, encrypted_key) VALUES (?, ?, ?, ?)',
    (sender, receiver, encrypted_message, encrypted_key)
)
```

#### Шаг 5: Получатель расшифровывает

```python
# encryption.py: decrypt_message()

# 1. Декодируем из base64
encrypted_message = base64.b64decode(encrypted_message_b64)
encrypted_key = base64.b64decode(encrypted_key_b64)

# 2. Расшифровываем AES ключ своим ПРИВАТНЫМ RSA ключом
fernet_key = private_key.decrypt(
    encrypted_key,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
)

# 3. Расшифровываем сообщение восстановленным AES ключом
fernet = Fernet(fernet_key)
decrypted_message = fernet.decrypt(encrypted_message)

return decrypted_message.decode('utf-8')
```

### 3. Почему это настоящее E2E?

```
СЦЕНАРИЙ: Злоумышленник захватил сервер

У него есть:
✓ База данных со всеми зашифрованными сообщениями
✓ Все публичные ключи пользователей
✓ Хеши паролей (бесполезны из-за bcrypt)

У него НЕТ:
✗ Приватных ключей пользователей (они только на клиентах!)
✗ AES ключей в открытом виде (зашифрованы RSA)

Может ли он прочитать сообщения?
❌ НЕТ! Без приватных ключей невозможно расшифровать AES ключи
❌ Без AES ключей невозможно расшифровать сообщения
✅ Это и есть E2E шифрование!
```

## 🔄 Протокол взаимодействия

### Формат сообщений (JSON)

Все сообщения между клиентом и сервером передаются в JSON формате через TCP сокеты.

#### 1. Регистрация

**Запрос:**
```json
{
    "command": "REGISTER",
    "username": "alice",
    "password": "secret123",
    "public_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgk..."
}
```

**Ответ:**
```json
{
    "success": true,
    "message": "Регистрация успешна"
}
```

#### 2. Вход

**Запрос:**
```json
{
    "command": "LOGIN",
    "username": "alice",
    "password": "secret123"
}
```

**Ответ:**
```json
{
    "success": true,
    "message": "Вход выполнен"
}
```

#### 3. Получение списка пользователей

**Запрос:**
```json
{
    "command": "GET_USERS",
    "username": "alice"
}
```

**Ответ:**
```json
{
    "success": true,
    "users": ["bob", "charlie", "dave"]
}
```

#### 4. Получение публичного ключа

**Запрос:**
```json
{
    "command": "GET_PUBLIC_KEY",
    "username": "bob"
}
```

**Ответ:**
```json
{
    "success": true,
    "public_key": "-----BEGIN PUBLIC KEY-----\n..."
}
```

#### 5. Отправка сообщения

**Запрос:**
```json
{
    "command": "SEND_MESSAGE",
    "sender": "alice",
    "receiver": "bob",
    "encrypted_message": "gAAAAABmK8xT...",
    "encrypted_key": "kR5mP3qL..."
}
```

**Ответ:**
```json
{
    "success": true
}
```

#### 6. Получение сообщений

**Запрос:**
```json
{
    "command": "GET_MESSAGES",
    "user1": "alice",
    "user2": "bob"
}
```

**Ответ:**
```json
{
    "success": true,
    "messages": [
        {
            "sender": "alice",
            "receiver": "bob",
            "encrypted_message": "gAAAAAB...",
            "encrypted_key": "kR5mP3...",
            "timestamp": "2024-01-15 10:30:00"
        }
    ]
}
```

## 🧵 Многопоточность на сервере

```python
# server.py: start()

while True:
    # Основной поток принимает подключения
    client_socket, address = server_socket.accept()

    # Для каждого клиента создаётся отдельный поток
    client_thread = threading.Thread(
        target=self.handle_client,
        args=(client_socket, address),
        daemon=True  # Поток завершится при выходе из программы
    )
    client_thread.start()
```

**Преимущества:**
- Сервер может обрабатывать несколько клиентов одновременно
- Блокировка одного клиента не влияет на других
- `daemon=True` - потоки автоматически завершаются при остановке сервера

**Thread-safety:**
```python
# Блокировка для безопасного доступа к словарю клиентов
self.clients_lock = threading.Lock()

with self.clients_lock:
    # Только один поток может изменять self.clients одновременно
    self.clients[username] = client_socket
```

## 🎨 GUI Architecture (CustomTkinter)

### Структура интерфейса

```
┌────────────────────────────────────────────────────────────┐
│ SecureChat - alice                                    ╳ ▭ ▬ │
├───────────────┬────────────────────────────────────────────┤
│ Чаты          │ 👤 bob                                     │
│               ├────────────────────────────────────────────┤
│ 👤 bob        │                                            │
│ 👤 charlie    │  ┌──────────────────────────┐             │
│ 👤 dave       │  │ Привет, как дела?        │  10:30     │
│               │  └──────────────────────────┘             │
│               │                                            │
│               │             ┌────────────────────────┐     │
│               │     10:31   │ Отлично, спасибо!     │     │
│               │             └────────────────────────┘     │
│               │                                            │
│               │  ┌──────────────────────────┐             │
│               │  │ Ты видел новый проект?   │  10:32     │
│               │  └──────────────────────────┘             │
│               │                                            │
├───────────────┼────────────────────────────────────────────┤
│               │ Введите сообщение...         [Отправить]  │
└───────────────┴────────────────────────────────────────────┘
```

### Компоненты

1. **Login Screen** (`show_login_screen()`):
   - Username Entry
   - Password Entry (с маскировкой)
   - Login Button
   - Register Button

2. **Main Screen** (`show_main_screen()`):
   - **Left Panel**: Список чатов (ScrollableFrame)
   - **Right Panel**:
     - Header: Имя текущего чата
     - Message Area: ScrollableFrame с сообщениями
     - Input Area: Entry + Send Button

3. **Message Bubbles** (`display_message()`):
   - Свои сообщения: справа, синие (#0084ff)
   - Чужие сообщения: слева, серые (#3a3a3a)
   - Timestamp внизу

### Цветовая схема

```python
# Основные цвета
Background:     #2b2b2b  (тёмно-серый)
Panels:         #1a1a1a  (почти чёрный)
Accent:         #0084ff  (синий - свои сообщения)
Secondary:      #3a3a3a  (серый - чужие сообщения)
Text:           #ffffff  (белый)
Text Secondary: #808080  (серый)
```

## 🔒 Безопасность

### Что защищено

1. **Сообщения**:
   - ✅ E2E шифрование (RSA-2048 + AES-128)
   - ✅ Новый ключ для каждого сообщения
   - ✅ OAEP padding для RSA
   - ✅ Authenticated encryption (Fernet)

2. **Пароли**:
   - ✅ bcrypt с автоматической солью
   - ✅ Cost factor 12 (по умолчанию)
   - ✅ Никогда не передаются в открытом виде после хеширования

3. **Ключи**:
   - ✅ Приватные ключи никогда не покидают клиент
   - ✅ Публичные ключи доступны всем (это нормально)

### Потенциальные улучшения для продакшн

1. **Forward Secrecy**:
   - Периодическое обновление ключей
   - Использование Diffie-Hellman для обмена ключами

2. **Аутентификация ключей**:
   - Проверка fingerprint ключа получателя
   - Защита от Man-in-the-Middle

3. **TLS/SSL**:
   - Шифрование соединения к серверу
   - Защита метаданных (кто с кем общается, когда)

4. **Perfect Forward Secrecy**:
   - Компрометация долгосрочного ключа не раскрывает старые сообщения
   - Использование ephemeral ключей

5. **Хранение ключей**:
   - Шифрование приватного ключа паролем пользователя
   - Использование OS keychain/keyring

## 📊 База данных (SQLite)

### Схема

#### Таблица `users`

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,          -- bcrypt hash
    public_key TEXT,                      -- PEM format RSA public key
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Таблица `messages`

```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT NOT NULL,
    receiver TEXT NOT NULL,
    encrypted_message TEXT NOT NULL,      -- base64 encoded AES encrypted
    encrypted_key TEXT NOT NULL,          -- base64 encoded RSA encrypted AES key
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender) REFERENCES users(username),
    FOREIGN KEY (receiver) REFERENCES users(username)
);
```

### Пример данных

**users:**
```
id | username | password_hash                    | public_key
---|----------|----------------------------------|-------------
1  | alice    | $2b$12$KIXxQ7P0...                | -----BEGIN PUBLIC KEY-----...
2  | bob      | $2b$12$mN5tR8W2...                | -----BEGIN PUBLIC KEY-----...
```

**messages:**
```
id | sender | receiver | encrypted_message        | encrypted_key           | timestamp
---|--------|----------|--------------------------|-------------------------|-------------------
1  | alice  | bob      | gAAAAABmK8xT...          | kR5mP3qLw8...          | 2024-01-15 10:30:00
2  | bob    | alice    | gAAAAABmK9Pf...          | mT7nQ5rNx9...          | 2024-01-15 10:31:00
```

Обратите внимание: даже с доступом к базе данных невозможно прочитать сообщения!

## 🚀 Производительность

### Время операций (примерные)

- **Генерация RSA ключей (2048 bit)**: ~100-200ms (делается один раз при старте)
- **Шифрование сообщения (гибридное)**: ~5-10ms
  - AES encryption: ~1ms
  - RSA encryption ключа: ~5ms
- **Расшифровка сообщения**: ~5-10ms
  - RSA decryption ключа: ~5ms
  - AES decryption: ~1ms
- **Хеширование пароля (bcrypt)**: ~100-200ms (намеренно медленно для защиты от брутфорса)

### Оптимизации

1. **Кэширование публичных ключей**:
   ```python
   self.public_keys_cache = {}  # Не запрашиваем повторно
   ```

2. **Гибридное шифрование**:
   - AES намного быстрее RSA для больших данных

3. **Асинхронные уведомления**:
   - Отдельный поток для прослушивания новых сообщений

## 🧪 Тестирование E2E шифрования

Простой тест для проверки:

```python
# encryption.py (в конце файла)

alice = E2EEncryption()
alice.generate_keys()

bob = E2EEncryption()
bob.generate_keys()

# Alice отправляет Bob
message = "Привет, Bob!"
encrypted_msg, encrypted_key = alice.encrypt_message(
    message,
    bob.get_public_key_string()
)

# Bob расшифровывает
decrypted = bob.decrypt_message(encrypted_msg, encrypted_key)

assert message == decrypted  # ✅ Работает!

# Попробуем расшифровать чужим ключом
charlie = E2EEncryption()
charlie.generate_keys()

try:
    charlie.decrypt_message(encrypted_msg, encrypted_key)
    # ❌ Не получится!
except:
    print("✅ Charlie не может расшифровать сообщение для Bob!")
```

## 📈 Масштабируемость

### Текущие ограничения

- **Максимум чатов**: 5 (можно изменить в коде)
- **Размер сообщения**: Ограничен только RSA (максимум ~190 байт для прямого шифрования, но мы используем гибридную схему, так что практически не ограничен)
- **Пользователи**: Ограничены только SQLite (миллионы возможны)

### Для увеличения масштаба

1. **PostgreSQL/MySQL** вместо SQLite
2. **Redis** для кэширования онлайн пользователей
3. **WebSockets** вместо polling для real-time обновлений
4. **Микросервисная архитектура**:
   - Auth Service
   - Message Service
   - Key Management Service
5. **Горизонтальное масштабирование** серверов

## 🎯 Выводы

Этот проект демонстрирует:
- ✅ Настоящее E2E шифрование
- ✅ Правильное использование криптографии
- ✅ Клиент-серверную архитектуру
- ✅ Многопоточность
- ✅ Современный GUI
- ✅ Кроссплатформенность

Идеально для учебного проекта по защите информации!
