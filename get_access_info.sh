#!/bin/bash

# Скрипт для получения информации о доступе к BANT Survey

echo "=== BANT Survey - Информация о доступе ==="
echo ""

# Получаем IP адрес
IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')

if [ -z "$IP" ]; then
    echo "❌ Не удалось определить IP адрес"
    exit 1
fi

echo "🌐 IP адрес: $IP"
echo ""

# Проверяем статус контейнеров
if docker-compose ps | grep -q "Up"; then
    echo "✅ Сервисы запущены"
else
    echo "❌ Сервисы не запущены. Выполните: make prod-up"
    exit 1
fi

# Проверяем наличие аутентификации
if [ -f "nginx_auth/.htpasswd" ]; then
    echo "🔐 Аутентификация включена"
    echo ""
    echo "📱 Адреса для доступа (с логином/паролем):"
    echo "   UI:  http://$IP"
    echo "   API: http://$IP/api"
    echo "   Docs: http://$IP/api/docs"
    echo ""
    echo "👤 Учетные данные:"
    echo "   Логин: admin"
    echo "   Пароль: password123"
    echo ""
    echo "🔧 Для изменения пароля: make setup-auth"
    echo "🔧 Для отключения аутентификации: make remove-auth"
else
    echo "🔓 Аутентификация отключена"
    echo ""
    echo "📱 Адреса для доступа (без пароля):"
    echo "   UI:  http://$IP"
    echo "   API: http://$IP/api"
    echo "   Docs: http://$IP/api/docs"
    echo ""
    echo "🔧 Для включения аутентификации: make setup-auth"
fi

echo ""
echo "⚠️  Важно:"
echo "   - Убедитесь, что порт 80 открыт в файрволе"
echo "   - Другие пользователи должны быть в той же сети"
echo "   - Для остановки: make prod-down"
