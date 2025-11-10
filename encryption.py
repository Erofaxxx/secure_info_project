"""
Модуль E2E шифрования для мессенджера
Использует гибридную схему: RSA для обмена ключами + Fernet (AES) для сообщений
"""

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.fernet import Fernet
import base64


class E2EEncryption:
    """Класс для обработки end-to-end шифрования"""

    def __init__(self):
        self.private_key = None
        self.public_key = None

    def generate_keys(self):
        """Генерация пары RSA ключей (публичный + приватный)"""
        # Генерируем RSA ключи 2048 бит
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()

    def get_public_key_string(self) -> str:
        """Получить публичный ключ в виде строки для отправки на сервер"""
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode('utf-8')

    def load_public_key_from_string(self, key_string: str):
        """Загрузить публичный ключ из строки"""
        return serialization.load_pem_public_key(key_string.encode('utf-8'))

    def encrypt_message(self, message: str, recipient_public_key_string: str) -> tuple:
        """
        Шифрование сообщения для получателя

        Процесс:
        1. Генерируется случайный Fernet ключ (AES-128)
        2. Сообщение шифруется этим ключом (быстро)
        3. Ключ шифруется публичным RSA ключом получателя (медленно, но ключ маленький)
        4. Возвращаются оба зашифрованных элемента

        Returns:
            (encrypted_message, encrypted_key) - оба в base64
        """
        # Генерируем случайный симметричный ключ для этого сообщения
        fernet_key = Fernet.generate_key()
        fernet = Fernet(fernet_key)

        # Шифруем сообщение симметричным ключом
        encrypted_message = fernet.encrypt(message.encode('utf-8'))

        # Шифруем сам ключ публичным ключом получателя
        recipient_public_key = self.load_public_key_from_string(recipient_public_key_string)
        encrypted_key = recipient_public_key.encrypt(
            fernet_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # Возвращаем в base64 для удобной передачи
        return (
            base64.b64encode(encrypted_message).decode('utf-8'),
            base64.b64encode(encrypted_key).decode('utf-8')
        )

    def decrypt_message(self, encrypted_message_b64: str, encrypted_key_b64: str) -> str:
        """
        Дешифрование полученного сообщения

        Процесс:
        1. Дешифруем Fernet ключ своим приватным RSA ключом
        2. Используем Fernet ключ для дешифровки сообщения

        Args:
            encrypted_message_b64: Зашифрованное сообщение в base64
            encrypted_key_b64: Зашифрованный ключ в base64

        Returns:
            Расшифрованное сообщение
        """
        # Декодируем из base64
        encrypted_message = base64.b64decode(encrypted_message_b64)
        encrypted_key = base64.b64decode(encrypted_key_b64)

        # Дешифруем ключ своим приватным ключом
        fernet_key = self.private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # Дешифруем сообщение восстановленным ключом
        fernet = Fernet(fernet_key)
        decrypted_message = fernet.decrypt(encrypted_message)

        return decrypted_message.decode('utf-8')


# Пример использования
if __name__ == '__main__':
    # Создаем шифровальщики для двух пользователей
    alice = E2EEncryption()
    alice.generate_keys()

    bob = E2EEncryption()
    bob.generate_keys()

    # Alice отправляет сообщение Bob
    message = "Привет, Bob! Это секретное сообщение 🔒"
    encrypted_msg, encrypted_key = alice.encrypt_message(
        message,
        bob.get_public_key_string()
    )

    print(f"Оригинальное сообщение: {message}")
    print(f"Зашифрованное: {encrypted_msg[:50]}...")
    print(f"Зашифрованный ключ: {encrypted_key[:50]}...")

    # Bob расшифровывает сообщение
    decrypted = bob.decrypt_message(encrypted_msg, encrypted_key)
    print(f"Расшифрованное: {decrypted}")
    print(f"Совпадает: {message == decrypted}")
