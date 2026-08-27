# 🚀 ИИ Пресс-секретарь — Скрипты деплоя

## 📁 Файлы

| Скрипт | Назначение |
|--------|-----------|
| `install.sh` | Полная установка (все в одном) |
| `deploy.sh` | Деплой приложения |
| `nginx-setup.sh` | Настройка Nginx |
| `ssl-setup.sh` | SSL сертификат (Let's Encrypt) |
| `backup.sh` | Бэкап проекта |
| `restore.sh` | Восстановление из бэкапа |
| `dev.sh` | Быстрый запуск в development |

## 🎯 Быстрая установка (3 шага)

### 1. Скопируй файлы на сервер

```bash
scp -r deploy.sh nginx-setup.sh ssl-setup.sh backup.sh restore.sh dev.sh README.md user@server:/opt/pressa/
```

### 2. Запусти установку

```bash
cd /opt/pressa
chmod +x *.sh
./install.sh
```

### 3. Настрой .env

```bash
nano /opt/pressa/.env
```

Заполни переменные:
```env
BOT_TOKEN=твой_токен_бота
PIAPI_API_KEY=твой_piapi_ключ
PIAPI_MODEL=gpt-4o
PROXY_URL=http://user:pass@host:port
CABINET_URL=https://твой_домен.com
```

## 📖 Использование отдельных скриптов

### Деплой

```bash
cd /opt/pressa
./deploy.sh
```

### Nginx

```bash
./nginx-setup.sh
```

Замените `твой_домен.com` на свой домен.

### SSL

```bash
./ssl-setup.sh
```

### Бэкап

```bash
./backup.sh
```

### Восстановление

```bash
./restore.sh
```

### Development

```bash
./dev.sh
```

## 🔧 Управление сервисом

```bash
# Статус
sudo systemctl status pressa

# Перезапуск
sudo systemctl restart pressa

# Остановка
sudo systemctl stop pressa

# Запуск
sudo systemctl start pressa

# Логи
sudo journalctl -u pressa -f

# Логи Nginx
sudo tail -f /var/log/nginx/pressa-error.log
```

## 🔄 Обновление

```bash
cd /opt/pressa
git pull origin main
./deploy.sh
```

## 📊 Мониторинг

```bash
# Приложение
sudo journalctl -u pressa -f

# Nginx
sudo tail -f /var/log/nginx/pressa-error.log
sudo tail -f /var/log/nginx/pressa-access.log

# Бэкапы
ls -lh /opt/backups/
```

## 🆘 Troubleshooting

### Сервис не запускается

```bash
sudo systemctl status pressa
sudo journalctl -u pressa -n 50
```

### Nginx не работает

```bash
sudo nginx -t
sudo systemctl restart nginx
```

### 500 ошибка

```bash
sudo journalctl -u pressa -n 100
sudo tail -f /var/log/nginx/pressa-error.log
```

### Проблемы с зависимостями

```bash
cd /opt/pressa
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 📦 Структура

```
/opt/pressa/
├── cabinet_service/      # Основной код
│   ├── app.py           # FastAPI
│   ├── templates/       # HTML
│   ├── static/          # CSS/JS
│   ├── media/           # Файлы
│   └── users.db         # База данных
├── ai_core/             # AI модули
├── venv/                # Python venv
├── .env                 # Переменные
├── requirements.txt     # Зависимости
├── deploy/              # Скрипты деплоя
│   ├── install.sh
│   ├── deploy.sh
│   ├── nginx-setup.sh
│   ├── ssl-setup.sh
│   ├── backup.sh
│   ├── restore.sh
│   └── dev.sh
└── README.md
```

## 🎓 Полезные команды

```bash
# Проверка порта
sudo netstat -tlnp | grep 8001

# Проверка RAM
free -h

# Проверка диска
df -h

# Перезагрузка
sudo reboot

# Остановка Nginx
sudo systemctl stop nginx

# Запуск Nginx
sudo systemctl start nginx
```

## 📞 Поддержка

Если что-то не работает — проверяй логи и убедись, что все переменные в `.env` заполнены.