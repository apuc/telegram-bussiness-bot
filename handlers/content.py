from database import get_user
from ai_core.neural_network import ContentGenerator
from keyboards.reply_keyboards import get_content_keyboard, BUSINESS_TYPES
import time

# Создаем экземпляр генератора контента
content_gen = ContentGenerator()

def handle_content_generation(message, bot, platform_text):
    """Генерирует контент для выбранной платформы"""
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user:
        bot.send_message(user_id, "❌ Ты не зарегистрирован. Напиши /start")
        return
    
    # Извлекаем платформу из текста кнопки
    platform_map = {
        "📝 Пост для Instagram": "instagram",
        "💼 Пост для LinkedIn": "linkedin",
        "📱 Пост для Telegram": "telegram",
        "🧵 Пост для Twitter/X": "twitter",
        "🎯 Рекламный пост": "ad"
    }
    
    platform = platform_map.get(platform_text, "instagram")
    platform_emoji = {
        "instagram": "📸",
        "linkedin": "💼",
        "telegram": "📱",
        "twitter": "🐦",
        "ad": "📢"
    }
    
    # Получаем данные пользователя
    business_type = BUSINESS_TYPES.get(str(user[4]), {}).get('name', 'Бизнес')
    description = user[5] or "не указано"
    
    # Отправляем статус "печатает"
    bot.send_chat_action(user_id, "typing")
    
    # Генерируем контент
    try:
        post = content_gen.generate_post(business_type, description, platform)
        
        # Отправляем результат
        response_text = f"""
{platform_emoji.get(platform, '📝')} **ГОТОВЫЙ ПОСТ ДЛЯ {platform.upper()}**

━━━━━━━━━━━━━━━━━━━━━━━

{post}

━━━━━━━━━━━━━━━━━━━━━━━

💡 **Совет:** 
• Добавь хештеги из поста
• Прикрепи фото или видео
• Укажи ссылку на свой сайт

📌 Хочешь другой вариант? Снова нажми "💡 Предложить контент"
        """
        
        bot.send_message(user_id, response_text, parse_mode='Markdown')
        
    except Exception as e:
        bot.send_message(
            user_id, 
            f"❌ Ошибка генерации: {e}\n\nПопробуй позже или обнови описание бизнеса."
        )
    
    # Показываем меню выбора платформы для следующего поста
    bot.send_message(
        user_id,
        "📱 Для какой соцсети нужен следующий пост?",
        reply_markup=get_content_keyboard()
    )