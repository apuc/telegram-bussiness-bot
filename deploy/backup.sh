#!/bin/bash

# === Бэкап проекта ===

set -e

APP_DIR="/opt/pressa"
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="pressa_$DATE.tar.gz"

echo "=== Создание бэкапа $BACKUP_NAME ==="

# Создание папки для бэкапов
mkdir -p $BACKUP_DIR

# Создание архива
cd $APP_DIR
tar -czf $BACKUP_DIR/$BACKUP_NAME \
    cabinet_service/users.db \
    cabinet_service/media \
    --exclude='cabinet_service/media/*' \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc'

# Удаление старых бэкапов (сохранять последние 7)
find $BACKUP_DIR -name "pressa_*.tar.gz" -mtime +7 -delete

echo "✓ Бэкап создан: $BACKUP_DIR/$BACKUP_NAME"
echo "Размер: $(du -h $BACKUP_DIR/$BACKUP_NAME | cut -f1)"
echo ""
echo "Список бэкапов:"
ls -lh $BACKUP_DIR/pressa_*.tar.gz | tail -5

# Опционально: копировать на другой сервер
# scp $BACKUP_DIR/$BACKUP_NAME user@backup-server:/backups/