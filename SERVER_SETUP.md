# 🖥️ Настройка сервера Ubuntu на Digital Ocean

Пошаговая инструкция по настройке безопасного сервера для SecureChat.

## 📋 Содержание

1. [Создание Droplet на Digital Ocean](#1-создание-droplet)
2. [Первоначальная настройка безопасности](#2-первоначальная-настройка)
3. [Установка Python и зависимостей](#3-установка-python)
4. [Развертывание приложения](#4-развертывание-приложения)
5. [Настройка Firewall](#5-настройка-firewall)
6. [Автозапуск сервера](#6-автозапуск)
7. [Мониторинг и обслуживание](#7-мониторинг)

---

## 1. Создание Droplet

### Шаг 1: Регистрация на Digital Ocean

1. Перейдите на [digitalocean.com](https://www.digitalocean.com/)
2. Создайте аккаунт (для студентов доступен GitHub Student Pack с кредитами)
3. Войдите в панель управления

### Шаг 2: Создание Droplet

1. Нажмите **"Create"** → **"Droplets"**
2. Выберите параметры:

   **Образ:**
   - Distribution: **Ubuntu 22.04 LTS x64**

   **План:**
   - Basic (для учебного проекта достаточно)
   - CPU: Regular
   - **$6/месяц** (1 GB RAM, 1 CPU, 25 GB SSD) - идеально для учебного проекта

   **Datacenter:**
   - Выберите ближайший к вам (например, Frankfurt для Европы)

   **Authentication:**
   - **SSH Key** (рекомендуется) или Password
   - Если SSH Key, следуйте инструкциям для генерации

   **Hostname:**
   - Например: `securechat-server`

3. Нажмите **"Create Droplet"**

4. Подождите ~1 минуту пока создастся сервер

5. **Запишите IP адрес** вашего сервера (например, `164.92.XXX.XXX`)

---

## 2. Первоначальная настройка

### Шаг 1: Подключение к серверу

**Из Windows:**
```bash
# Если используете SSH ключ
ssh -i путь/к/ключу root@164.92.XXX.XXX

# Если используете пароль
ssh root@164.92.XXX.XXX
```

**Из macOS/Linux:**
```bash
ssh root@164.92.XXX.XXX
```

### Шаг 2: Обновление системы

```bash
# Обновляем список пакетов
apt update

# Обновляем все пакеты
apt upgrade -y

# Перезагружаем (опционально, если было обновление ядра)
# reboot
```

### Шаг 3: Создание нового пользователя (ВАЖНО!)

Не работайте под root! Создадим отдельного пользователя:

```bash
# Создаём пользователя
adduser messenger

# Добавляем в группу sudo (для выполнения команд от root)
usermod -aG sudo messenger

# Переключаемся на нового пользователя
su - messenger
```

### Шаг 4: Настройка SSH для нового пользователя

**Если используете SSH ключи:**

```bash
# На сервере (под пользователем messenger)
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Копируем ключ от root
sudo cp /root/.ssh/authorized_keys ~/.ssh/
sudo chown messenger:messenger ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

**Проверка:** Откройте новое окно терминала и попробуйте:
```bash
ssh messenger@164.92.XXX.XXX
```

### Шаг 5: Настройка SSH безопасности

```bash
# Редактируем конфиг SSH
sudo nano /etc/ssh/sshd_config
```

Найдите и измените следующие строки:

```
# Отключаем вход под root
PermitRootLogin no

# Отключаем аутентификацию по паролю (если используете SSH ключи)
PasswordAuthentication no

# Разрешаем только вход по ключу
PubkeyAuthentication yes

# Отключаем пустые пароли
PermitEmptyPasswords no
```

Сохраните: `Ctrl+X`, затем `Y`, затем `Enter`

Перезапустите SSH:
```bash
sudo systemctl restart sshd
```

---

## 3. Установка Python

### Шаг 1: Установка Python 3 и pip

```bash
# Устанавливаем Python 3 и pip
sudo apt install python3 python3-pip python3-venv -y

# Проверяем версию
python3 --version  # Должно быть 3.10+
```

### Шаг 2: Установка git (для загрузки проекта)

```bash
sudo apt install git -y
```

---

## 4. Развертывание приложения

### Шаг 1: Загрузка проекта

**Вариант А: Через git (если проект в репозитории)**

```bash
cd ~
git clone https://github.com/ваш-username/secure_info_project.git
cd secure_info_project
```

**Вариант Б: Через SCP (если файлы на локальном компьютере)**

На **вашем компьютере**:
```bash
# Создайте архив
tar -czf securechat.tar.gz server.py encryption.py requirements.txt

# Загрузите на сервер
scp securechat.tar.gz messenger@164.92.XXX.XXX:~/
```

На **сервере**:
```bash
tar -xzf securechat.tar.gz
cd securechat  # или как вы назвали папку
```

**Вариант В: Создание файлов вручную**

```bash
mkdir ~/securechat
cd ~/securechat

# Создайте файлы server.py, encryption.py, requirements.txt
# и скопируйте в них код
nano server.py
# Вставьте код сервера, сохраните (Ctrl+X, Y, Enter)

nano encryption.py
# Вставьте код шифрования, сохраните

nano requirements.txt
# Вставьте зависимости, сохраните
```

### Шаг 2: Создание виртуального окружения

```bash
# Создаём виртуальное окружение
python3 -m venv venv

# Активируем
source venv/bin/activate

# Обновляем pip
pip install --upgrade pip
```

### Шаг 3: Установка зависимостей

```bash
# Устанавливаем зависимости проекта
pip install -r requirements.txt
```

### Шаг 4: Тестовый запуск

```bash
# Запускаем сервер для проверки
python server.py
```

Вы должны увидеть:
```
🚀 Сервер мессенджера запущен на 0.0.0.0:5555
Ожидание подключений...
```

Нажмите `Ctrl+C` для остановки.

---

## 5. Настройка Firewall

### Шаг 1: UFW (Uncomplicated Firewall)

```bash
# Проверяем статус
sudo ufw status

# Если не активен, настраиваем
# ВАЖНО: сначала разрешаем SSH, иначе заблокируете себя!
sudo ufw allow 22/tcp comment 'SSH'

# Разрешаем порт мессенджера
sudo ufw allow 5555/tcp comment 'SecureChat'

# Включаем firewall
sudo ufw enable

# Проверяем правила
sudo ufw status numbered
```

Должно быть примерно так:
```
Status: active

     To                         Action      From
     --                         ------      ----
[ 1] 22/tcp                     ALLOW IN    Anywhere                  # SSH
[ 2] 5555/tcp                   ALLOW IN    Anywhere                  # SecureChat
```

### Шаг 2: Digital Ocean Firewall (опционально, дополнительная защита)

1. В панели Digital Ocean перейдите в **Networking** → **Firewalls**
2. Создайте новый Firewall:
   - **Inbound Rules:**
     - SSH (22) - All IPv4, All IPv6
     - Custom (5555) - All IPv4, All IPv6
   - **Outbound Rules:**
     - All TCP, All UDP (оставьте по умолчанию)
3. Примените к вашему Droplet

---

## 6. Автозапуск

Настроим автоматический запуск сервера при загрузке системы с помощью systemd.

### Шаг 1: Создание systemd service

```bash
sudo nano /etc/systemd/system/securechat.service
```

Вставьте следующее содержимое (измените пути если нужно):

```ini
[Unit]
Description=SecureChat E2E Encrypted Messenger Server
After=network.target

[Service]
Type=simple
User=messenger
WorkingDirectory=/home/messenger/securechat
Environment="PATH=/home/messenger/securechat/venv/bin"
ExecStart=/home/messenger/securechat/venv/bin/python /home/messenger/securechat/server.py
Restart=always
RestartSec=10

# Логирование
StandardOutput=append:/home/messenger/securechat/server.log
StandardError=append:/home/messenger/securechat/server.error.log

[Install]
WantedBy=multi-user.target
```

Сохраните: `Ctrl+X`, `Y`, `Enter`

### Шаг 2: Запуск сервиса

```bash
# Перезагружаем systemd
sudo systemctl daemon-reload

# Запускаем сервис
sudo systemctl start securechat

# Проверяем статус
sudo systemctl status securechat
```

Должно быть `active (running)` и зелёная точка.

### Шаг 3: Включение автозапуска

```bash
# Включаем автозапуск при загрузке системы
sudo systemctl enable securechat

# Проверяем что включен
sudo systemctl is-enabled securechat
```

### Управление сервисом

```bash
# Запуск
sudo systemctl start securechat

# Остановка
sudo systemctl stop securechat

# Перезапуск
sudo systemctl restart securechat

# Статус
sudo systemctl status securechat

# Логи
sudo journalctl -u securechat -f  # следить за логами в реальном времени
sudo journalctl -u securechat -n 50  # последние 50 строк
```

---

## 7. Мониторинг

### Проверка работы сервера

```bash
# Проверка что порт слушается
sudo netstat -tulpn | grep 5555

# Или
sudo ss -tulpn | grep 5555
```

Должно показать:
```
tcp   LISTEN   0   5   0.0.0.0:5555   0.0.0.0:*   users:(("python",pid=1234,fd=3))
```

### Просмотр логов

```bash
# Логи systemd
sudo journalctl -u securechat -f

# Или если настроили логи в файл
tail -f ~/securechat/server.log
tail -f ~/securechat/server.error.log
```

### Проверка использования ресурсов

```bash
# Использование CPU и памяти
htop

# Или
top

# Информация о процессе
ps aux | grep python
```

### Проверка базы данных

```bash
cd ~/securechat

# Просмотр пользователей
sqlite3 messenger.db "SELECT username, created_at FROM users;"

# Количество сообщений
sqlite3 messenger.db "SELECT COUNT(*) FROM messages;"

# Выход
sqlite3 messenger.db
# Внутри sqlite:
.tables
SELECT * FROM users;
.quit
```

---

## 8. Тестирование подключения

### Из локальной сети или другого сервера

```bash
# Проверка доступности порта
nc -zv 164.92.XXX.XXX 5555

# Или
telnet 164.92.XXX.XXX 5555
```

### Из клиентского приложения

На **вашем компьютере**:

```bash
# Запустите клиент
python client.py

# Введите IP сервера
164.92.XXX.XXX
```

Попробуйте зарегистрироваться и отправить сообщение!

---

## 9. Безопасность (дополнительно)

### Fail2Ban - защита от брутфорса SSH

```bash
# Установка
sudo apt install fail2ban -y

# Копируем конфиг
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local

# Редактируем
sudo nano /etc/fail2ban/jail.local
```

Найдите секцию `[sshd]` и убедитесь что:
```
[sshd]
enabled = true
port = 22
maxretry = 3
bantime = 3600
```

Запускаем:
```bash
sudo systemctl start fail2ban
sudo systemctl enable fail2ban

# Проверка
sudo fail2ban-client status sshd
```

### Автоматические обновления безопасности

```bash
# Установка
sudo apt install unattended-upgrades -y

# Настройка
sudo dpkg-reconfigure -plow unattended-upgrades
# Выберите "Yes"
```

### Ограничение подключений к серверу (rate limiting)

Если хотите ограничить количество подключений к порту 5555:

```bash
# Ограничиваем до 5 новых подключений в минуту с одного IP
sudo ufw limit 5555/tcp comment 'Rate limit SecureChat'
```

---

## 10. Резервное копирование

### Бэкап базы данных

Создайте скрипт для автоматического бэкапа:

```bash
nano ~/backup.sh
```

Вставьте:
```bash
#!/bin/bash

# Путь к проекту
PROJECT_DIR="/home/messenger/securechat"
BACKUP_DIR="/home/messenger/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Создаём папку для бэкапов
mkdir -p $BACKUP_DIR

# Копируем базу данных
cp $PROJECT_DIR/messenger.db $BACKUP_DIR/messenger_$DATE.db

# Удаляем бэкапы старше 7 дней
find $BACKUP_DIR -name "messenger_*.db" -mtime +7 -delete

echo "Backup completed: messenger_$DATE.db"
```

Сохраните и сделайте исполняемым:
```bash
chmod +x ~/backup.sh
```

### Автоматический бэкап через cron

```bash
crontab -e
```

Добавьте строку (бэкап каждый день в 3:00):
```
0 3 * * * /home/messenger/backup.sh >> /home/messenger/backup.log 2>&1
```

---

## 11. Обслуживание

### Регулярные задачи

**Еженедельно:**
- Проверяйте логи: `sudo journalctl -u securechat --since "1 week ago"`
- Проверяйте использование диска: `df -h`
- Проверяйте обновления: `sudo apt update && sudo apt list --upgradable`

**Ежемесячно:**
- Обновляйте систему: `sudo apt update && sudo apt upgrade -y`
- Проверяйте бэкапы: `ls -lh ~/backups/`
- Анализируйте логи fail2ban: `sudo fail2ban-client status sshd`

### Обновление приложения

```bash
cd ~/securechat

# Остановите сервер
sudo systemctl stop securechat

# Сделайте бэкап
./backup.sh

# Обновите код (если через git)
git pull

# Или загрузите новые файлы через scp

# Обновите зависимости
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Запустите сервер
sudo systemctl start securechat

# Проверьте статус
sudo systemctl status securechat
```

---

## 12. Решение проблем

### Сервер не запускается

```bash
# Проверьте логи
sudo journalctl -u securechat -n 100

# Проверьте что порт не занят
sudo netstat -tulpn | grep 5555

# Проверьте права на файлы
ls -la ~/securechat/

# Попробуйте запустить вручную
cd ~/securechat
source venv/bin/activate
python server.py
```

### Клиенты не могут подключиться

```bash
# Проверьте firewall
sudo ufw status

# Проверьте что сервер слушает на всех интерфейсах
sudo netstat -tulpn | grep 5555
# Должно быть 0.0.0.0:5555, а не 127.0.0.1:5555

# Проверьте доступность из вне
# На вашем компьютере:
telnet 164.92.XXX.XXX 5555
```

### База данных повреждена

```bash
# Остановите сервер
sudo systemctl stop securechat

# Проверьте базу
cd ~/securechat
sqlite3 messenger.db "PRAGMA integrity_check;"

# Если есть ошибки, восстановите из бэкапа
cp ~/backups/messenger_YYYYMMDD_HHMMSS.db ./messenger.db

# Запустите сервер
sudo systemctl start securechat
```

---

## 📊 Итоговая конфигурация

После выполнения всех шагов у вас будет:

- ✅ Ubuntu 22.04 LTS сервер
- ✅ Отдельный пользователь (не root)
- ✅ SSH доступ только по ключу
- ✅ UFW firewall с открытыми портами 22 и 5555
- ✅ Python 3.10+ с виртуальным окружением
- ✅ SecureChat сервер запущен как systemd service
- ✅ Автозапуск при перезагрузке
- ✅ Fail2Ban для защиты SSH
- ✅ Автоматические обновления безопасности
- ✅ Ежедневные бэкапы базы данных

## 🎯 Быстрая проверка

Выполните эти команды для проверки что всё работает:

```bash
# 1. Сервис запущен
sudo systemctl status securechat | grep "active (running)"

# 2. Порт слушается
sudo netstat -tulpn | grep 5555

# 3. Firewall настроен
sudo ufw status | grep 5555

# 4. Логи без ошибок
sudo journalctl -u securechat -n 20 --no-pager

# 5. База данных существует
ls -lh ~/securechat/messenger.db
```

Если все 5 команд выполнились успешно - всё работает отлично! 🎉

---

## 💡 Дополнительные улучшения (опционально)

### HTTPS/TLS для веб-доступа

Если планируете веб-интерфейс:

```bash
sudo apt install certbot -y
sudo certbot certonly --standalone -d ваш-домен.ru
```

### Nginx как reverse proxy

```bash
sudo apt install nginx -y
# Настройте проксирование на порт 5555
```

### Мониторинг с помощью Prometheus + Grafana

Для продвинутого мониторинга (выходит за рамки учебного проекта).

---

## 📝 Чек-лист для преподавателя

Для демонстрации можете показать:

- [ ] Работающий сервер на удалённом сервере
- [ ] Подключение клиентов с разных компьютеров
- [ ] Обмен сообщениями между пользователями
- [ ] Зашифрованные сообщения в базе данных
- [ ] Логи работы сервера
- [ ] Настроенный firewall (ufw status)
- [ ] systemd service (systemctl status)
- [ ] Защиту SSH (fail2ban status)

---

**Готово!** Ваш сервер SecureChat настроен и защищён для учебного проекта! 🚀🔒
