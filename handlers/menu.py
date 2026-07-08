from database import get_user, update_user_description
from keyboards.reply_keyboards import get_main_menu_keyboard, get_settings_keyboard, get_content_keyboard, BUSINESS_TYPES
from handlers.content import handle_content_generation

def show_main_menu(user_id, bot):
    """Показывает главное меню"""
    user = get_user(user_id)
    if user:
        bot.send_message(
            user_id,
            "🏠 Главное меню\n\nВыбери действие:",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        bot.send_message(
            user_id,
            "❌ Ты не зарегистрирован. Напиши /start",
            reply_markup=None
        )

def handle_menu_choice(message, bot):
    """Обрабатывает выбор в главном меню"""
    user_id = message.from_user.id
    text = message.text
    
    if text == "📋 Мой профиль":
        show_profile(message, bot)
        return True
    
    elif text == "✏️ Обновить описание":
        # Запускаем процесс обновления описания
        from handlers.registration import user_data
        user_data[user_id] = {'step': 'edit_description'}
        bot.send_message(
            user_id, 
            "📝 Напиши новое описание своего бизнеса:",
            reply_markup=None
        )
        return True
    
    elif text == "📊 Статистика":
        show_stats(message, bot)
        return True
    
    elif text == "💡 Предложить контент":
        # Показываем выбор платформы для контента
        bot.send_message(
            user_id,
            "📱 Для какой соцсети нужен контент?",
            reply_markup=get_content_keyboard()
        )
        return True
    
    elif text == "⚙️ Настройки":
        bot.send_message(
            user_id,
            "⚙️ Настройки:",
            reply_markup=get_settings_keyboard()
        )
        return True
    
    # Обработка кнопок настроек
    elif text == "🔔 Включить уведомления":
        bot.send_message(user_id, "✅ Уведомления включены!")
        return True
    
    elif text == "🔕 Выключить уведомления":
        bot.send_message(user_id, "🔕 Уведомления выключены!")
        return True
    
    elif text == "📝 Сменить тему бизнеса":
        bot.send_message(
            user_id,
            "Напиши новое описание бизнеса:",
            reply_markup=None
        )
        return True
    
    elif text == "⬅️ Назад в меню":
        show_main_menu(user_id, bot)
        return True
    
    # Обработка выбора платформы для контента
    elif text in ["📝 Пост для Instagram", "💼 Пост для LinkedIn", 
                  "📱 Пост для Telegram", "🧵 Пост для Twitter/X", 
                  "🎯 Рекламный пост"]:
        handle_content_generation(message, bot, text)
        return True
    
    return False

def show_profile(message, bot):
    """Показывает профиль пользователя"""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(user_id, "❌ Ты не зарегистрирован. Напиши /start")
        return
    
    business_name = BUSINESS_TYPES.get(str(user[4]), {}).get('name', 'Не указан')
    
    profile_text = f"""
📋 **ТВОЙ ПРОФИЛЬ**
━━━━━━━━━━━━━━━━━

👤 **Имя:** {user[2]}
📱 **Телефон:** {user[3]}
🏢 **Вид бизнеса:** {business_name}
📝 **Описание:**
{user[5]}

━━━━━━━━━━━━━━━━━
💡 Хочешь обновить описание? Нажми "✏️ Обновить описание"
    """
    bot.send_message(user_id, profile_text, parse_mode='Markdown')
    show_main_menu(user_id, bot)

def show_stats(message, bot):
    """Показывает статистику"""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(user_id, "❌ Ты не зарегистрирован. Напиши /start")
        return
    
    stats_text = f"""
📊 **СТАТИСТИКА**

👤 Ты зарегистрирован как предприниматель
📋 Тип: {BUSINESS_TYPES.get(str(user[4]), {}).get('name', 'Не указан')}
📝 Описание: {user[5][:50]}...

💡 Совет: Регулярно обновляй информацию о бизнесе,
чтобы я мог давать тебе точные рекомендации!
    """
    bot.send_message(user_id, stats_text, parse_mode='Markdown')
    show_main_menu(user_id, bot)