#!/bin/bash

# === Восстановление из бэкапа ===

set -e

BACKUP_DIR="/opt/backups"
APP_DIR="/opt/pressa"

echo "=== Восстановление из бэкапа ==="
echo ""
echo "Доступные бэкапы:"
ls -1 $BACKUP_DIR/pressa_*.tar.gz 2>/dev/null || echo "Бэкапы не найдены"

echo ""
read -p "Введите имя файла бэкапа (например, pressa_20260827_143022.tar.gz): " BACKUP_FILE

if [ ! -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
    echo "❌ Файл не найден: $BACKUP_DIR/$BACKUP_FILE"
    exit 1
fi

echo ""
echo "Восстановление: $BACKUP_DIR/$BACKUP_FILE"
read -p "Продолжить? (y/N): " CONFIRM

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Отмена"
    exit 0
fi

# Остановка сервиса
echo "Остановка сервиса..."
sudo systemctl stop pressa

# Создание папки
mkdir -p $APP_DIR/cabinet_service

# Восстановление базы данных
echo "Восстановление базы данных..."
tar -xzf $BACKUP_DIR/$BACKUP_FILE -C $APP_DIR users.db

# Восстановление медиа
echo "Восстановление медиа..."
tar -xzf $BACKUP_DIR/$BACKUP_FILE -C $APP_DIR cabinet_service/media

# Установка прав
echo "Установка прав..."
sudo chown -R www-data:www-data $APP_DIR/cabinet_service

# Перезапуск
echo "Перезапуск сервиса..."
sudo systemctl start pressa

echo ""
echo "✓ Восстановление завершено!"
echo "Проверь статус: sudo systemctl status pressa"