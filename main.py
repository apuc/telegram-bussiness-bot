import telebot
import requests
import sys
import os
import threading
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from telebot import apihelper

from config import TOKEN
from database import get_user
from handlers.registration import process_registration, is_in_registration
from handlers.menu import show_main_menu, handle_menu_choice
from keyboards.reply_keyboards import get_main_menu_keyboard

# === НАСТРОЙКА ДЛЯ ОБХОДА БЛОКИРОВОК ===
session = requests.Session()
retry = Retry(total=5, backoff_factor=1)
adapter = HTTPAdapter(max_retries=retry)
session.mount('https://', adapter)

apihelper.session = session
apihelper.CONNECT_TIMEOUT = 30
apihelper.READ_TIMEOUT = 30

# === ИНИЦИАЛИЗАЦИЯ БОТА ===
bot = telebot.TeleBot(TOKEN)

# === ФЛАГ ДЛЯ УПРАВЛЕНИЯ БОТОМ ===
bot_running = True

# === КОМАНДА /start ===
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if user:
        bot.send_message(
            user_id,
            f"👋 С возвращением, {user[2]}!",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Начинаем регистрацию
    from handlers.registration import user_data as reg_data
    reg_data[user_id] = {'step': 1}
    bot.send_message(
        user_id,
        "👋 Привет! Я твой бизнес-помощник.\n\n"
        "Давай познакомимся! Как тебя зовут?\n"
        "(Напиши своё имя)"
    )

# === КОМАНДА /stop - ОСТАНОВИТЬ БОТА (ДЛЯ ВСЕХ) ===
@bot.message_handler(commands=['stop'])
def stop_bot(message):
    user_id = message.from_user.id
    global bot_running
    
    bot_running = False
    
    bot.send_message(user_id, "🛑 Вы остановилибота...")
    print(f"🛑 Бот остановлен пользователем {user_id}")
    
    # Останавливаем бота
    bot.stop_polling()
    os._exit(0)

# === КОМАНДА /restart - ПЕРЕЗАПУСТИТЬ БОТА (ДЛЯ ВСЕХ) ===
@bot.message_handler(commands=['restart'])
def restart_bot(message):
    user_id = message.from_user.id
    
    bot.send_message(user_id, "🔄 Перезапускаю бота...")
    print(f"🔄 Перезапуск бота пользователем {user_id}")
    
    # Перезапускаем
    bot.stop_polling()
    os.execv(sys.executable, ['python'] + sys.argv)

# === КОМАНДА /status - СТАТУС БОТА (ДЛЯ ВСЕХ) ===
@bot.message_handler(commands=['status'])
def status_bot(message):
    user_id = message.from_user.id
    
    import datetime
    now = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    
    # Проверяем, есть ли PIAPI_API_KEY
    try:
        from config import PIAPI_API_KEY
        piapi_status = "подключен ✅" if PIAPI_API_KEY else "не подключен ⚠️"
    except:
        piapi_status = "не подключен ⚠️"

    status_text = f"""
📊 **СТАТУС БОТА**

🟢 Состояние: **Активен** ✅
📅 Текущее время: {now}

📋 **Информация:**
• Бот запущен и работает
• База данных: подключена ✅
• PiAPI: {piapi_status}

💡 **Команды управления:**
/stop - остановить бота
/restart - перезапустить бота
/status - этот статус
    """
    bot.send_message(user_id, status_text, parse_mode='Markdown')

# === КОМАНДА /help - ПОМОЩЬ ===
@bot.message_handler(commands=['help'])
def help_command(message):
    user_id = message.from_user.id
    
    help_text = """
🤖 **ПОМОЩЬ ПО БОТУ**

📋 **Основные команды:**
/start - начать работу или открыть меню
/help - показать эту справку
/status - статус бота
/stop - остановить бота
/restart - перезапустить бота

📱 **Меню после регистрации:**
📋 Мой профиль - посмотреть свои данные
✏️ Обновить описание - изменить описание бизнеса
📊 Статистика - статистика
💡 Предложить контент - сгенерировать пост для соцсетей
⚙️ Настройки - настройки бота
🗂 Личный кабинет - расширенный профиль, пост в своём стиле, контент-план, история постов и статистика

💡 **Как использовать:**
1. Напиши /start
2. Пройди регистрацию
3. Используй кнопки меню
4. Нажми "💡 Предложить контент" для генерации поста
    """
    bot.send_message(user_id, help_text, parse_mode='Markdown')

# === ОБРАБОТКА ВСЕХ СООБЩЕНИЙ ===
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    global bot_running
    
    if not bot_running:
        bot.send_message(message.chat.id, "🛑 Бот остановлен. Напиши /restart для перезапуска.")
        return
    
    user_id = message.from_user.id
    text = message.text
    
    # Проверяем, зарегистрирован ли пользователь
    user = get_user(user_id)
    
    if user:
        # Если пользователь в процессе обновления описания
        from handlers.registration import user_data as reg_data
        if user_id in reg_data and reg_data[user_id].get('step') == 'edit_description':
            from database import update_user_description
            update_user_description(user_id, text)
            del reg_data[user_id]
            bot.send_message(
                user_id,
                "✅ Описание обновлено!",
                reply_markup=get_main_menu_keyboard()
            )
            return

        # Обрабатываем выбор в меню
        if handle_menu_choice(message, bot):
            return
        
        # Если ничего не подошло - показываем меню
        bot.send_message(
            user_id,
            "Используй кнопки меню 👇",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    # Если пользователь НЕ зарегистрирован - регистрируем
    if is_in_registration(user_id):
        process_registration(message, bot)
    else:
        bot.send_message(
            user_id,
            "❌ Ты не зарегистрирован. Напиши /start"
        )

# === ЗАПУСК БОТА ===
if __name__ == '__main__':
    from cabinet_service.runner import run as run_cabinet_service
    cabinet_thread = threading.Thread(target=run_cabinet_service, daemon=True)
    cabinet_thread.start()
    print("🗂 Сервис личного кабинета запущен в фоне")

    print("🤖 БОТ ЗАПУЩЕН!")
    print("📋 Команды:")
    print("  /start   - начать работу")
    print("  /help    - помощь")
    print("  /status  - статус бота")
    print("  /stop    - остановить бота")
    print("  /restart - перезапустить бота")
    print("✅ Используй кнопки для навигации")

    try:
        bot.infinity_polling(timeout=30)
    except KeyboardInterrupt:
        print("🛑 Бот остановлен вручную (Ctrl+C)")
    except Exception as e:
        print(f"❌ Ошибка: {e}")