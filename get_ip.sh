#!/bin/bash

# Получить IP адрес для внешнего доступа
echo "=== BANT Survey - Внешний доступ ==="
echo ""

# Получаем IP адрес
IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')

if [ -z "$IP" ]; then
    echo "❌ Не удалось определить IP адрес"
    exit 1
fi

echo "🌐 Ваш IP адрес: $IP"
echo ""
echo "📱 Доступные адреса для других пользователей:"
echo "   UI:  http://$IP"
echo "   API: http://$IP/api"
echo "   Docs: http://$IP/api/docs"
echo ""
echo "⚠️  Убедитесь, что:"
echo "   1. Порт 80 открыт в файрволе"
echo "   2. Docker контейнеры запущены (make prod-up)"
echo "   3. Другие пользователи находятся в той же сети"
echo ""
echo "🔧 Для остановки: make prod-down"
