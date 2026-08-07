import os
import secrets
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Токен бота
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("❌ BOT_TOKEN не найден в .env файле!")
    print("👉 Создай файл .env и добавь: BOT_TOKEN=твой_токен")

# Ключ PiAPI
PIAPI_API_KEY = os.getenv("PIAPI_API_KEY")
PIAPI_MODEL = os.getenv("PIAPI_MODEL", "gpt-4o")

# Модель генерации картинок через PiAPI (список доступных: /v1/models)
PIAPI_IMAGE_MODEL = os.getenv("PIAPI_IMAGE_MODEL", "gpt-image-1")

# Прокси для доступа к внешним API (PiAPI и др.).
# Формат в .env: PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS
PROXY_HOST = os.getenv("PROXY_HOST")
PROXY_PORT = os.getenv("PROXY_PORT")
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")

def get_proxies():
    """Возвращает dict прокси для requests, или None, если прокси не настроен."""
    if not (PROXY_HOST and PROXY_PORT):
        return None
    auth = f"{PROXY_USER}:{PROXY_PASS}@" if (PROXY_USER and PROXY_PASS) else ""
    proxy = f"http://{auth}{PROXY_HOST}:{PROXY_PORT}"
    return {"http": proxy, "https": proxy}

# Сервис "Личный кабинет" (отдельный FastAPI-процесс, веб-интерфейс на браузере)
CABINET_SERVICE_HOST = os.getenv("CABINET_SERVICE_HOST", "127.0.0.1")
CABINET_SERVICE_PORT = int(os.getenv("CABINET_SERVICE_PORT", "8001"))

# Публичный адрес кабинета - именно эту ссылку бот присылает пользователю.
# Для реального использования (не localhost) нужно задать в .env настоящий
# домен/IP, доступный из браузера пользователя.
CABINET_WEB_URL = os.getenv("CABINET_WEB_URL", f"http://{CABINET_SERVICE_HOST}:{CABINET_SERVICE_PORT}")

# Ключ подписи cookie-сессий веб-кабинета
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    print("⚠️ SECRET_KEY не найден в .env - сгенерирован временный ключ.")
    print("👉 Добавь SECRET_KEY в .env, иначе все сессии слетают при каждом перезапуске.")

# Проверяем, что ключ загрузился
if not PIAPI_API_KEY:
    print("❌ PIAPI_API_KEY не найден в .env файле!")
    print("👉 Создай файл .env и добавь: PIAPI_API_KEY=твой_ключ")
else:
    print("✅ PIAPI_API_KEY загружен!")

