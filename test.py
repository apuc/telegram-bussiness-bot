import telebot
from config import TOKEN
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from telebot import apihelper

# === ОБХОД БЛОКИРОВКИ ===
session = requests.Session()
retry = Retry(total=5, backoff_factor=1)
adapter = HTTPAdapter(max_retries=retry)
session.mount('https://', adapter)
session.mount('http://', adapter)

apihelper.session = session
apihelper.CONNECT_TIMEOUT = 30
apihelper.READ_TIMEOUT = 30

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "✅ БОТ РАБОТАЕТ! Я тебя слышу!")

@bot.message_handler(func=lambda message: True)
def echo(message):
    bot.send_message(message.chat.id, f"Ты написал: {message.text}")

print("🔄 Проверяю подключение к Telegram...")

# Проверяем подключение
try:
    me = bot.get_me()
    print(f"✅ Подключено! Бот: @{me.username}")
except Exception as e:
    print(f"❌ НЕ ПОДКЛЮЧЕНО! Ошибка: {e}")
    print("👉 Включите VPN!")
    exit()

print("🚀 Бот готов к работе! Напиши /start")

bot.infinity_polling(timeout=30)