#!/usr/bin/env python3
"""
Демонстрация работы E2E шифрования SecureChat
Этот скрипт показывает как работает шифрование между двумя пользователями
"""

from encryption import E2EEncryption
import time


def print_section(title):
    """Красиво печатает заголовок секции"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_step(number, description):
    """Печатает шаг с номером"""
    print(f"\n[Шаг {number}] {description}")
    time.sleep(0.5)


def main():
    print("\n" + "🔒" * 35)
    print("  ДЕМОНСТРАЦИЯ E2E ШИФРОВАНИЯ SECURECHAT")
    print("🔒" * 35)

    # ==================== СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ ====================
    print_section("1. СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ И ГЕНЕРАЦИЯ КЛЮЧЕЙ")

    print_step(1.1, "Создаём пользователя Alice...")
    alice = E2EEncryption()
    alice.generate_keys()
    print("   ✅ Alice создана")
    print("   ✅ Сгенерирована пара RSA ключей (2048 бит)")
    print(f"   📤 Публичный ключ Alice (первые 100 символов):")
    print(f"      {alice.get_public_key_string()[:100]}...")

    print_step(1.2, "Создаём пользователя Bob...")
    bob = E2EEncryption()
    bob.generate_keys()
    print("   ✅ Bob создан")
    print("   ✅ Сгенерирована пара RSA ключей (2048 бит)")
    print(f"   📤 Публичный ключ Bob (первые 100 символов):")
    print(f"      {bob.get_public_key_string()[:100]}...")

    print_step(1.3, "Создаём злоумышленника Eve...")
    eve = E2EEncryption()
    eve.generate_keys()
    print("   ✅ Eve создана")
    print("   ⚠️  Eve попытается перехватить сообщения!")

    # ==================== ОТПРАВКА СООБЩЕНИЯ ====================
    print_section("2. ALICE ОТПРАВЛЯЕТ СООБЩЕНИЕ BOB")

    original_message = "Привет, Bob! Это секретное сообщение от Alice 🔒"

    print_step(2.1, "Alice пишет сообщение...")
    print(f"   💬 Оригинальное сообщение: \"{original_message}\"")
    print(f"   📏 Длина: {len(original_message)} символов")

    print_step(2.2, "Alice шифрует сообщение...")
    print("   📋 Процесс:")
    print("      1. Alice генерирует случайный AES ключ")
    print("      2. Шифрует сообщение этим AES ключом (быстро)")
    print("      3. Шифрует AES ключ публичным RSA ключом Bob (медленно, но ключ маленький)")

    encrypted_message, encrypted_key = alice.encrypt_message(
        original_message,
        bob.get_public_key_string()
    )

    print("   ✅ Сообщение зашифровано!")
    print(f"   🔐 Зашифрованное сообщение (первые 80 символов):")
    print(f"      {encrypted_message[:80]}...")
    print(f"   🔑 Зашифрованный AES ключ (первые 80 символов):")
    print(f"      {encrypted_key[:80]}...")

    print_step(2.3, "Alice отправляет на сервер...")
    print("   📤 Отправляется:")
    print("      - encrypted_message (зашифрованный текст)")
    print("      - encrypted_key (зашифрованный AES ключ)")
    print("   ✅ Данные отправлены на сервер")

    # ==================== СЕРВЕР ====================
    print_section("3. СЕРВЕР ПОЛУЧАЕТ И СОХРАНЯЕТ")

    print_step(3.1, "Сервер получает данные...")
    print("   📥 Сервер видит:")
    print(f"      - sender: Alice")
    print(f"      - receiver: Bob")
    print(f"      - encrypted_message: {encrypted_message[:40]}...")
    print(f"      - encrypted_key: {encrypted_key[:40]}...")

    print_step(3.2, "Сервер пытается прочитать сообщение...")
    print("   ❓ Может ли сервер расшифровать?")
    print("   ❌ НЕТ! У сервера нет приватного ключа Bob")
    print("   ✅ Это и есть E2E шифрование!")

    print_step(3.3, "Сервер сохраняет в базу данных...")
    print("   💾 Сохранено в БД как есть (зашифрованное)")
    print("   ✅ Данные готовы для доставки Bob")

    # ==================== BOB ПОЛУЧАЕТ ====================
    print_section("4. BOB ПОЛУЧАЕТ И РАСШИФРОВЫВАЕТ")

    print_step(4.1, "Bob получает зашифрованные данные...")
    print(f"   📥 Bob получил:")
    print(f"      - encrypted_message: {encrypted_message[:40]}...")
    print(f"      - encrypted_key: {encrypted_key[:40]}...")

    print_step(4.2, "Bob расшифровывает...")
    print("   📋 Процесс:")
    print("      1. Bob расшифровывает AES ключ своим приватным RSA ключом")
    print("      2. Bob расшифровывает сообщение восстановленным AES ключом")

    decrypted_message = bob.decrypt_message(encrypted_message, encrypted_key)

    print("   ✅ Сообщение расшифровано!")
    print(f"   💬 Расшифрованное сообщение: \"{decrypted_message}\"")

    print_step(4.3, "Проверка целостности...")
    if original_message == decrypted_message:
        print("   ✅ УСПЕХ! Сообщение совпадает с оригиналом")
        print(f"   ✅ Оригинал:        \"{original_message}\"")
        print(f"   ✅ Расшифрованное:  \"{decrypted_message}\"")
    else:
        print("   ❌ ОШИБКА! Сообщения не совпадают")

    # ==================== EVE ПЫТАЕТСЯ ПЕРЕХВАТИТЬ ====================
    print_section("5. EVE ПЫТАЕТСЯ ПЕРЕХВАТИТЬ СООБЩЕНИЕ")

    print_step(5.1, "Eve перехватывает трафик...")
    print("   🕵️  Eve видит то же, что и сервер:")
    print(f"      - encrypted_message: {encrypted_message[:40]}...")
    print(f"      - encrypted_key: {encrypted_key[:40]}...")

    print_step(5.2, "Eve пытается расшифровать...")
    print("   ❓ Может ли Eve прочитать сообщение?")

    try:
        eve_attempt = eve.decrypt_message(encrypted_message, encrypted_key)
        print("   ❌ Eve смогла расшифровать! (не должно было случиться)")
    except Exception as e:
        print("   ✅ Eve НЕ МОЖЕТ расшифровать!")
        print(f"   ✅ Причина: {type(e).__name__}")
        print("   ✅ У Eve нет приватного ключа Bob")
        print("   ✅ E2E шифрование РАБОТАЕТ!")

    # ==================== ОБРАТНОЕ СООБЩЕНИЕ ====================
    print_section("6. BOB ОТВЕЧАЕТ ALICE")

    bob_message = "Привет, Alice! Я получил твоё сообщение 👍"

    print_step(6.1, "Bob отправляет ответ...")
    print(f"   💬 Сообщение Bob: \"{bob_message}\"")

    encrypted_bob_msg, encrypted_bob_key = bob.encrypt_message(
        bob_message,
        alice.get_public_key_string()
    )

    print("   ✅ Bob зашифровал сообщение публичным ключом Alice")
    print(f"   🔐 Зашифровано: {encrypted_bob_msg[:60]}...")

    print_step(6.2, "Alice расшифровывает ответ...")
    decrypted_bob_msg = alice.decrypt_message(encrypted_bob_msg, encrypted_bob_key)
    print(f"   💬 Alice прочитала: \"{decrypted_bob_msg}\"")
    print("   ✅ Двусторонняя коммуникация работает!")

    # ==================== ИТОГИ ====================
    print_section("7. ИТОГИ")

    print("\n✅ Что мы продемонстрировали:\n")
    print("   1. ✅ Alice и Bob могут безопасно обмениваться сообщениями")
    print("   2. ✅ Сервер не может прочитать сообщения")
    print("   3. ✅ Злоумышленник Eve не может перехватить и расшифровать")
    print("   4. ✅ Только получатель с нужным приватным ключом может прочитать")
    print("   5. ✅ Двусторонняя коммуникация работает")

    print("\n🔐 Почему это безопасно:\n")
    print("   • RSA 2048 бит - современный стандарт асимметричного шифрования")
    print("   • AES (Fernet) - быстрое и надёжное симметричное шифрование")
    print("   • Гибридная схема - лучшее из обоих миров")
    print("   • Новый AES ключ для каждого сообщения")
    print("   • Приватные ключи НИКОГДА не покидают устройства")

    print("\n⚠️  Важно понимать:\n")
    print("   • Сервер хранит только ЗАШИФРОВАННЫЕ сообщения")
    print("   • Даже администратор сервера не может прочитать переписку")
    print("   • Это настоящее End-to-End шифрование!")

    print("\n" + "=" * 70)
    print("  ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА УСПЕШНО! ✅")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    main()
