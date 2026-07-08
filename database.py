import sqlite3

def create_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            name TEXT,
            phone TEXT,
            business_type INTEGER,
            description TEXT,
            registered BOOLEAN DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных создана!")

def save_user(telegram_id, name, phone, business_type, description):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO users (telegram_id, name, phone, business_type, description, registered)
        VALUES (?, ?, ?, ?, ?, 1)
    ''', (telegram_id, name, phone, business_type, description))
    
    conn.commit()
    conn.close()
    print(f"✅ Пользователь {name} сохранен!")

def get_user(telegram_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
    user = cursor.fetchone()
    
    conn.close()
    return user

def update_user_description(telegram_id, description):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET description = ? WHERE telegram_id = ?', (description, telegram_id))
    conn.commit()
    conn.close()

# Создаем базу при первом импорте
create_db()