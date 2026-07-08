from handlers.menu import show_main_menu
from keyboards.reply_keyboards import get_phone_keyboard, get_business_types_keyboard, BUSINESS_TYPES
from database import get_user, save_user

# Хранилище для временных данных пользователей
user_data = {}

def process_registration(message, bot):
    """Обработка регистрации"""
    user_id = message.from_user.id
    text = message.text
    step = user_data[user_id].get('step', 1)
    
    if step == 1:
        # Сохраняем имя
        user_data[user_id]['name'] = text
        user_data[user_id]['step'] = 2
        
        bot.send_message(
            user_id,
            f"👋 Приятно познакомиться, {text}!\n\n"
            "📱 Теперь отправь мне свой номер телефона.\n"
            "Нажми на кнопку ниже 👇",
            reply_markup=get_phone_keyboard()
        )
    
    elif step == 2:
        # Сохраняем телефон
        if message.contact:
            phone = message.contact.phone_number
        else:
            phone = text
        
        user_data[user_id]['phone'] = phone
        user_data[user_id]['step'] = 3
        
        bot.send_message(
            user_id,
            "📋 Выбери свой вид предпринимательства:",
            reply_markup=get_business_types_keyboard()
        )
    
    elif step == 3:
        # Проверяем выбор вида бизнеса
        selected_type = None
        for key, value in BUSINESS_TYPES.items():
            if text == f"{value['emoji']} {key}. {value['name']}":
                selected_type = int(key)
                break
        
        if not selected_type:
            bot.send_message(
                user_id,
                "❌ Пожалуйста, выбери вид бизнеса из кнопок ниже:",
                reply_markup=get_business_types_keyboard()
            )
            return
        
        user_data[user_id]['business_type'] = selected_type
        user_data[user_id]['step'] = 4
        
        bot.send_message(
            user_id,
            f"✅ Отлично! Ты выбрал: {BUSINESS_TYPES[str(selected_type)]['name']}\n\n"
            "📝 Теперь расскажи немного о своем бизнесе:\n"
            "(Чем занимаешься? Сколько лет на рынке? Какие цели?)",
            reply_markup=None
        )
    
    elif step == 4:
        # Сохраняем описание
        description = text
        
        save_user(
            user_id,
            user_data[user_id]['name'],
            user_data[user_id]['phone'],
            user_data[user_id]['business_type'],
            description
        )
        
        # Сохраняем вид бизнеса для дальнейшего использования
        business_type_name = BUSINESS_TYPES[str(user_data[user_id]['business_type'])]['name']
        
        # Очищаем временные данные
        del user_data[user_id]
        
        welcome_text = f"""
🎉 ПОЗДРАВЛЯЮ! РЕГИСТРАЦИЯ ЗАВЕРШЕНА!

✅ Ты зарегистрирован как предприниматель!
📋 Тип бизнеса: {business_type_name}

💡 Теперь я буду помогать тебе:
• Генерировать контент для соцсетей
• Давать советы по бизнесу
• Анализировать твою нишу

Нажми «💡 Предложить контент» в меню! 👇
        """
        bot.send_message(user_id, welcome_text)
        show_main_menu(user_id, bot)

def is_in_registration(user_id):
    """Проверяет, находится ли пользователь в процессе регистрации"""
    return user_id in user_data