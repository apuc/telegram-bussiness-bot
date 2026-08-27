#!/bin/bash

# === Полная установка ИИ Пресс-секретарь ===

set -e

echo "=== Полная установка ИИ Пресс-секретарь ==="
echo ""

# 1. Установка системных зависимостей
echo "[1/7] Установка системных зависимостей..."
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3-pip nginx certbot python3-certbot-nginx

# 2. Клонирование проекта
echo "[2/7] Клонирование проекта..."
sudo mkdir -p /opt/pressa
git clone https://github.com/твой_репозиторий/pressa.git /opt/pressa
cd /opt/pressa

# 3. Деплой
echo "[3/7] Деплой приложения..."
chmod +x deploy.sh
./deploy.sh

# 4. Nginx
echo "[4/7] Настройка Nginx..."
chmod +x nginx-setup.sh
./nginx-setup.sh

# 5. SSL
echo "[5/7] Настройка SSL..."
read -p "Есть домен? (y/N): " HAS_DOMAIN
if [ "$HAS_DOMAIN" == "y" ] || [ "$HAS_DOMAIN" == "Y" ]; then
    read -p "Введите домен (например, example.com): " DOMAIN
    chmod +x ssl-setup.sh
    ./ssl-setup.sh
fi

# 6. Бэкап
echo "[6/7] Настройка бэкапов..."
chmod +x backup.sh
echo "0 3 * * * /opt/pressa/deploy/backup.sh" | crontab -

# 7. Проверка
echo "[7/7] Проверка..."
sudo systemctl status pressa --no-pager -l

echo ""
echo "=== Установка завершена! ==="
echo ""
echo "Доступ:"
echo "  - Без Nginx: http://localhost:8001"
echo "  - С Nginx: http://$(hostname -I | awk '{print $1}'):80"
echo ""
echo "Следующие шаги:"
echo "  1. Отредактируй .env файл: nano /opt/pressa/.env"
echo "  2. Заполни переменные окружения"
echo "  3. Перезапусти сервис: sudo systemctl restart pressa"
echo ""
echo "Управление:"
echo "  - Статус: sudo systemctl status pressa"
echo "  - Логи: sudo journalctl -u pressa -f"
echo "  - Бэкап: sudo /opt/pressa/deploy/backup.sh"
echo "  - Восстановление: sudo /opt/pressa/deploy/restore.sh"