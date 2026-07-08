import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Токен бота
TOKEN = "8876908400:AAGb4_ayjfhWuUI_evP8vvc5YUUiG8jxepE"

# Ключ Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Проверяем, что ключ загрузился
if not GROQ_API_KEY:
    print("❌ GROQ_API_KEY не найден в .env файле!")
    print("👉 Создай файл .env и добавь: GROQ_API_KEY=твой_ключ")
else:
    print("✅ GROQ_API_KEY загружен!")

