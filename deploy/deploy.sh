#!/bin/bash

# === Деплой ИИ Пресс-секретарь ===
# Клонирует/обновляет код, ставит зависимости, настраивает systemd-сервис.

set -e

APP_DIR="/opt/pressa"
REPO_URL="https://github.com/apuc/telegram-bussiness-bot.git"
SERVICE_NAME="pressa"
PYTHON_BIN="$APP_DIR/venv/bin/python"
# Сервис работает от отдельного пользователя без shell и sudo, не от root
SERVICE_USER="pressa"

echo "=== Деплой ИИ Пресс-секретарь ==="
echo ""

# 1. Клонирование или обновление кода
if [ -d "$APP_DIR/.git" ]; then
    echo "[1/5] Обновление кода из git..."
    cd "$APP_DIR"
    # Каталог принадлежит пользователю сервиса — разрешаем git работать в нём
    git config --global --add safe.directory "$APP_DIR"
    git pull origin main
else
    echo "[1/5] Клонирование репозитория..."
    sudo mkdir -p "$APP_DIR"
    sudo chown "$USER":"$USER" "$APP_DIR"
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

# 2. Виртуальное окружение и зависимости
echo "[2/5] Установка зависимостей..."
if [ ! -d "$APP_DIR/venv" ]; then
    python3 -m venv "$APP_DIR/venv"
fi
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

# 3. Проверка .env
echo "[3/5] Проверка .env..."
if [ ! -f "$APP_DIR/.env" ]; then
    echo "⚠️  Файл .env не найден!"
    echo "   Скопируй его на сервер: scp .env apuc@SERVER:/opt/pressa/.env"
    echo "   Или создай вручную по образцу config.py"
fi

# 4. systemd-сервис
echo "[4/5] Настройка systemd-сервиса..."
if ! id "$SERVICE_USER" >/dev/null 2>&1; then
    sudo useradd --system --home-dir "$APP_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi
# Код читает, пишет только базу, медиа и логи; .env доступен только сервису
sudo chown -R "$SERVICE_USER":"$SERVICE_USER" "$APP_DIR"
[ -f "$APP_DIR/.env" ] && sudo chmod 600 "$APP_DIR/.env"
# В базе лежат ключи API и токены TenChat — читать её может только сервис
[ -f "$APP_DIR/users.db" ] && sudo chmod 600 "$APP_DIR/users.db"
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=AI Press Secretary (Telegram bot + Cabinet)
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$PYTHON_BIN $APP_DIR/main.py
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME

# 5. Перезапуск
echo "[5/5] Перезапуск сервиса..."
sudo systemctl restart $SERVICE_NAME

echo ""
echo "=== Деплой завершён! ==="
echo "Статус: sudo systemctl status $SERVICE_NAME"
echo "Логи:   sudo journalctl -u $SERVICE_NAME -f"
