from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# === 9 ВИДОВ ПРЕДПРИНИМАТЕЛЕЙ ===
BUSINESS_TYPES = {
    '1': {'name': '🛒 Розничная торговля', 'emoji': '🛒'},
    '2': {'name': '🏭 Производство', 'emoji': '🏭'},
    '3': {'name': '💻 IT-услуги', 'emoji': '💻'},
    '4': {'name': '📚 Образование', 'emoji': '📚'},
    '5': {'name': '🏥 Медицина', 'emoji': '🏥'},
    '6': {'name': '🚚 Логистика', 'emoji': '🚚'},
    '7': {'name': '🏨 Гостиничный бизнес', 'emoji': '🏨'},
    '8': {'name': '🎨 Маркетинг и реклама', 'emoji': '🎨'},
    '9': {'name': '🔧 Услуги (ремонт, клининг)', 'emoji': '🔧'}
}

def get_main_menu_keyboard():
    """Главное меню после регистрации"""
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(
        KeyboardButton("📋 Мой профиль"),
        KeyboardButton("✏️ Обновить описание"),
        KeyboardButton("📊 Статистика"),
        KeyboardButton("💡 Предложить контент"),
        KeyboardButton("⚙️ Настройки"),
        KeyboardButton("🗂 Личный кабинет")
    )
    return keyboard

def get_cabinet_link_keyboard(cabinet_web_url):
    """Инлайн-кнопка со ссылкой на веб-версию личного кабинета"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🌐 Открыть личный кабинет", url=cabinet_web_url))
    return keyboard

def get_business_types_keyboard():
    """Клавиатура с 9 видами предпринимателей"""
    keyboard = ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
    buttons = []
    for key, value in BUSINESS_TYPES.items():
        buttons.append(KeyboardButton(f"{value['emoji']} {key}. {value['name']}"))
    
    row1 = buttons[0:3]
    row2 = buttons[3:6]
    row3 = buttons[6:9]
    
    keyboard.add(*row1)
    keyboard.add(*row2)
    keyboard.add(*row3)
    
    return keyboard

def get_phone_keyboard():
    """Клавиатура с запросом номера телефона"""
    keyboard = ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    button = KeyboardButton("📱 Отправить номер телефона", request_contact=True)
    keyboard.add(button)
    return keyboard

def get_settings_keyboard():
    """Клавиатура настроек"""
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(
        KeyboardButton("🔔 Включить уведомления"),
        KeyboardButton("🔕 Выключить уведомления"),
        KeyboardButton("📝 Сменить тему бизнеса"),
        KeyboardButton("⬅️ Назад в меню")
    )
    return keyboard

def get_content_keyboard():
    """Клавиатура для генерации контента"""
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(
        KeyboardButton("📝 Пост для Instagram"),
        KeyboardButton("💼 Пост для LinkedIn"),
        KeyboardButton("📱 Пост для Telegram"),
        KeyboardButton("🧵 Пост для Twitter/X"),
        KeyboardButton("🎯 Рекламный пост"),
        KeyboardButton("⬅️ Назад в меню")
    )
    return keyboard