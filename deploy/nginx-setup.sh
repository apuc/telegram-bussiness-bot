#!/bin/bash

# === Настройка Nginx для ИИ Пресс-секретарь ===
# Создаёт reverse-proxy конфиг для домена на порт 8061.

set -e

DOMAIN="${1:-press.my-dpr.ru}"
PORT="${2:-8061}"

echo "=== Настройка Nginx для $DOMAIN ==="
echo ""

# Проверяем, что конфиг ещё не существует
if [ -f "/etc/nginx/sites-available/$DOMAIN" ]; then
    echo "⚠️  Конфиг /etc/nginx/sites-available/$DOMAIN уже существует."
    read -p "Перезаписать? (y/N): " CONFIRM
    if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
        echo "Отмена"
        exit 0
    fi
fi

# Создаём конфиг (HTTP, SSL добавит certbot)
sudo tee /etc/nginx/sites-available/$DOMAIN > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_read_timeout 300s;
    }
}
EOF

# Включаем сайт
sudo ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/$DOMAIN

# Проверяем конфиг
echo "Проверка конфигурации Nginx..."
sudo nginx -t

# Перезагружаем Nginx
echo "Перезагрузка Nginx..."
sudo systemctl reload nginx

echo ""
echo "=== Nginx настроен! ==="
echo "Домен: http://$DOMAIN -> http://127.0.0.1:$PORT"
echo ""
echo "Следующий шаг — SSL: ./ssl-setup.sh $DOMAIN"
