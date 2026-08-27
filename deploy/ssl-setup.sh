#!/bin/bash

# === Настройка SSL (Let's Encrypt) для ИИ Пресс-секретарь ===

set -e

DOMAIN="${1:-press.my-dpr.ru}"

echo "=== Настройка SSL для $DOMAIN ==="
echo ""

# Проверяем наличие certbot
if ! command -v certbot &> /dev/null; then
    echo "Установка certbot..."
    sudo apt update
    sudo apt install -y certbot python3-certbot-nginx
fi

# Выпускаем сертификат и настраиваем Nginx автоматически
echo "Выпуск SSL-сертификата..."
sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --redirect

echo ""
echo "=== SSL настроен! ==="
echo "Домен: https://$DOMAIN"
echo ""
echo "Проверка:"
echo "  sudo certbot certificates"
echo "  sudo systemctl status nginx"
