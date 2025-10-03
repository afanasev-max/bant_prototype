#!/bin/bash

# Скрипт для настройки HTTP Basic Authentication

echo "=== BANT Survey - Настройка аутентификации ==="
echo ""

# Проверяем наличие htpasswd
if ! command -v htpasswd &> /dev/null; then
    echo "❌ htpasswd не найден. Установите apache2-utils:"
    echo "   macOS: brew install httpd"
    echo "   Ubuntu/Debian: sudo apt-get install apache2-utils"
    echo "   CentOS/RHEL: sudo yum install httpd-tools"
    exit 1
fi

# Создаем директорию для .htpasswd
mkdir -p nginx_auth

# Запрашиваем логин и пароль
echo "🔐 Настройка аутентификации:"
read -p "Введите логин (по умолчанию: admin): " username
username=${username:-admin}

read -s -p "Введите пароль: " password
echo ""

if [ -z "$password" ]; then
    echo "❌ Пароль не может быть пустым"
    exit 1
fi

# Генерируем .htpasswd файл
htpasswd -cb nginx_auth/.htpasswd "$username" "$password"

if [ $? -eq 0 ]; then
    echo "✅ Аутентификация настроена успешно!"
    echo "   Логин: $username"
    echo "   Пароль: [скрыт]"
    echo ""
    echo "🔄 Перезапускаем nginx для применения изменений..."
    docker-compose restart nginx
    echo ""
    echo "🌐 Теперь доступ будет по адресу:"
    echo "   http://YOUR_IP (с запросом логина/пароля)"
    echo ""
    echo "📋 Учетные данные для доступа:"
    echo "   Логин: $username"
    echo "   Пароль: [введенный вами пароль]"
else
    echo "❌ Ошибка при создании файла аутентификации"
    exit 1
fi
