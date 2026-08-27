# ИИ Пресс-секретарь

AI-powered content generation and publishing platform for entrepreneurs and community organizations.

## 🚀 Быстрый старт

### Локальный запуск (Windows)

```powershell
# 1. Клонировать репозиторий
git clone https://github.com/username/pressa.git
cd pressa

# 2. Создать виртуальное окружение
python -m venv venv
venv\Scripts\activate

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Создать .env файл
# Скопируй config.py в .env и заполни переменные

# 5. Запустить сервер
python -m uvicorn cabinet_service.app:app --host 127.0.0.1 --port 8001
```

Открой в браузере: http://127.0.0.1:8001

### Деплой на сервер (Linux)

Смотри папку `deploy/`:

```bash
cd deploy
chmod +x *.sh
./install.sh
```

Или пошагово:
1. `./deploy.sh` — установка приложения
2. `./nginx-setup.sh` — настройка веб-сервера
3. `./ssl-setup.sh` — SSL сертификат

## 📋 Требования

- Python 3.12+
- SQLite (встроен в Python)
- Nginx (для production)
- Доступ к AI API (PiAPI, OpenAI, OpenRouter)

## 🔧 Переменные окружения

Создай файл `.env` в корне проекта:

```env
BOT_TOKEN=your_telegram_bot_token
PIAPI_API_KEY=your_piapi_key
PIAPI_MODEL=gpt-4o
PROXY_URL=http://user:pass@host:port
CABINET_URL=https://your-domain.com
```

## 📁 Структура проекта

```
pressa/
├── cabinet_service/      # Веб-приложение (FastAPI)
│   ├── app.py           # Основной файл
│   ├── templates/       # HTML шаблоны
│   ├── static/          # CSS/JS
│   └── media/           # Загруженные файлы
├── ai_core/             # AI модули
│   ├── neural_network.py    # Генерация текста
│   ├── image_generator.py   # Генерация изображений
│   ├── social_analyzer.py   # Анализ соцсетей
│   └── telegram_publisher.py # Публикация в Telegram
├── deploy/              # Скрипты деплоя
├── config.py            # Конфигурация
├── requirements.txt     # Зависимости
└── README.md            # Этот файл
```

## 🎯 Возможности

- ✍️ Генерация постов с помощью AI
- 🎨 Генерация изображений
- 📅 Контент-план
- 📊 Медиа-образ (бренд-бук)
- 📤 Публикация в Telegram
- 🤖 Чат с AI для редактирования постов
- 📱 Адаптивный дизайн

## 🛠️ Технологии

- **Backend:** Python, FastAPI, SQLite
- **Frontend:** HTML, CSS, JavaScript (vanilla)
- **AI:** OpenAI GPT-4, PiAPI, OpenRouter
- **Deploy:** Gunicorn, Nginx, systemd

## 📄 Лицензия

MIT