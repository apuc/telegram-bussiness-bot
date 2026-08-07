import sqlite3

# Поля профиля, которые разрешено менять через "личный кабинет"
EDITABLE_FIELDS = {'name', 'phone', 'business_type', 'description'}

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

    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'registered' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN registered BOOLEAN DEFAULT 0')
        print("✅ Колонка 'registered' добавлена в таблицу users")
    if 'created_at' not in columns:
        # SQLite не разрешает non-constant DEFAULT в ALTER TABLE ADD COLUMN
        cursor.execute('ALTER TABLE users ADD COLUMN created_at TIMESTAMP')
        cursor.execute('UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL')
        print("✅ Колонка 'created_at' добавлена в таблицу users")
    if 'email' not in columns:
        # Без UNIQUE - SQLite не позволяет добавить UNIQUE через ALTER TABLE,
        # уникальность email проверяется на уровне приложения (get_user_by_email)
        cursor.execute('ALTER TABLE users ADD COLUMN email TEXT')
        print("✅ Колонка 'email' добавлена в таблицу users")
    if 'password_hash' not in columns:
        cursor.execute('ALTER TABLE users ADD COLUMN password_hash TEXT')
        print("✅ Колонка 'password_hash' добавлена в таблицу users")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            platform TEXT,
            content TEXT,
            style TEXT,
            wishes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute("PRAGMA table_info(posts)")
    posts_columns = [row[1] for row in cursor.fetchall()]
    if 'user_id' not in posts_columns:
        # Посты веб-кабинета привязаны к users.id, посты из бота - к telegram_id
        cursor.execute('ALTER TABLE posts ADD COLUMN user_id INTEGER')
        print("✅ Колонка 'user_id' добавлена в таблицу posts")

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS content_plan (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            day INTEGER,
            platform TEXT,
            idea TEXT,
            status TEXT DEFAULT 'planned',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS media (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            prompt TEXT,
            style TEXT,
            filename TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

def update_user_field(telegram_id, field, value):
    """Обновляет одно поле профиля. field обязан быть из EDITABLE_FIELDS."""
    if field not in EDITABLE_FIELDS:
        raise ValueError(f"Поле '{field}' нельзя редактировать")

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(f'UPDATE users SET {field} = ? WHERE telegram_id = ?', (value, telegram_id))
    conn.commit()
    conn.close()

def delete_user(telegram_id):
    """Удаляет пользователя и всю его историю постов."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE telegram_id = ?', (telegram_id,))
    cursor.execute('DELETE FROM posts WHERE telegram_id = ?', (telegram_id,))
    conn.commit()
    conn.close()

def save_post(telegram_id, platform, content, style=None, wishes=None):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO posts (telegram_id, platform, content, style, wishes)
        VALUES (?, ?, ?, ?, ?)
    ''', (telegram_id, platform, content, style, wishes))
    conn.commit()
    conn.close()

def get_posts(telegram_id, limit=10):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT platform, content, style, wishes, created_at
        FROM posts
        WHERE telegram_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (telegram_id, limit))
    posts = cursor.fetchall()
    conn.close()
    return posts

def get_stats(telegram_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute('SELECT created_at FROM users WHERE telegram_id = ?', (telegram_id,))
    row = cursor.fetchone()
    created_at = row[0] if row else None

    cursor.execute('SELECT COUNT(*) FROM posts WHERE telegram_id = ?', (telegram_id,))
    total_posts = cursor.fetchone()[0]

    cursor.execute('''
        SELECT platform, COUNT(*) FROM posts
        WHERE telegram_id = ?
        GROUP BY platform
    ''', (telegram_id,))
    by_platform = dict(cursor.fetchall())

    conn.close()
    return {
        'created_at': created_at,
        'total_posts': total_posts,
        'by_platform': by_platform
    }

# === ФУНКЦИИ ДЛЯ ВЕБ-КАБИНЕТА (ключ - внутренний users.id, не telegram_id) ===

def _row_conn():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn


def get_user_by_email(email):
    conn = _row_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    conn = _row_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_web_user(email, password_hash, name, phone, business_type, description):
    """Создаёт пользователя веб-кабинета (без telegram_id). Возвращает id нового пользователя."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO users (name, phone, business_type, description, registered, created_at, email, password_hash)
        VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP, ?, ?)
    ''', (name, phone, business_type, description, email, password_hash))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id


def update_user_field_by_id(user_id, field, value):
    """Обновляет одно поле профиля по внутреннему id. field обязан быть из EDITABLE_FIELDS."""
    if field not in EDITABLE_FIELDS:
        raise ValueError(f"Поле '{field}' нельзя редактировать")

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(f'UPDATE users SET {field} = ? WHERE id = ?', (value, user_id))
    conn.commit()
    conn.close()


def delete_user_by_id(user_id):
    """Удаляет пользователя веб-кабинета и всю его историю постов."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    cursor.execute('DELETE FROM posts WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()


def save_post_for_user(user_id, platform, content, style=None, wishes=None):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO posts (user_id, platform, content, style, wishes)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, platform, content, style, wishes))
    conn.commit()
    conn.close()


def get_posts_for_user(user_id, limit=10):
    conn = _row_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, platform, content, style, wishes, created_at
        FROM posts
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    ''', (user_id, limit))
    posts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return posts


def get_stats_for_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    cursor.execute('SELECT created_at FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    created_at = row[0] if row else None

    cursor.execute('SELECT COUNT(*) FROM posts WHERE user_id = ?', (user_id,))
    total_posts = cursor.fetchone()[0]

    cursor.execute('''
        SELECT platform, COUNT(*) FROM posts
        WHERE user_id = ?
        GROUP BY platform
    ''', (user_id,))
    by_platform = dict(cursor.fetchall())

    conn.close()
    return {
        'created_at': created_at,
        'total_posts': total_posts,
        'by_platform': by_platform
    }


# === УПРАВЛЕНИЕ ПОСТАМИ (веб-кабинет) ===

def get_post_by_id_for_user(post_id, user_id):
    """Возвращает один пост веб-пользователя (только если он принадлежит user_id)."""
    conn = _row_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM posts WHERE id = ? AND user_id = ?', (post_id, user_id))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_post_content(user_id, post_id, content):
    """Редактирует текст поста. Меняет только посты, принадлежащие user_id."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE posts SET content = ? WHERE id = ? AND user_id = ?', (content, post_id, user_id))
    conn.commit()
    conn.close()


def delete_post_by_id(user_id, post_id):
    """Удаляет пост. Удаляет только посты, принадлежащие user_id."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM posts WHERE id = ? AND user_id = ?', (post_id, user_id))
    conn.commit()
    conn.close()


# === КОНТЕНТ-ПЛАН (веб-кабинет) ===

PLAN_STATUSES = ('planned', 'published', 'postponed')

def replace_plan_for_user(user_id, plan_items):
    """Полностью заменяет контент-план пользователя новыми пунктами.
    plan_items: список словарей {'day': int, 'platform': str, 'idea': str}"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM content_plan WHERE user_id = ?', (user_id,))
    cursor.executemany(
        'INSERT INTO content_plan (user_id, day, platform, idea) VALUES (?, ?, ?, ?)',
        [(user_id, item['day'], item['platform'], item['idea']) for item in plan_items]
    )
    conn.commit()
    conn.close()


def get_plan_for_user(user_id):
    conn = _row_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM content_plan WHERE user_id = ? ORDER BY day, id', (user_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def update_plan_status(user_id, item_id, status):
    if status not in PLAN_STATUSES:
        raise ValueError(f"Недопустимый статус '{status}'")
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE content_plan SET status = ? WHERE id = ? AND user_id = ?',
        (status, item_id, user_id)
    )
    conn.commit()
    conn.close()


def delete_plan_item(user_id, item_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM content_plan WHERE id = ? AND user_id = ?', (item_id, user_id))
    conn.commit()
    conn.close()


def get_plan_stats_for_user(user_id):
    """Считает пункты плана по статусам: {'planned': n, 'published': n, ...}"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT status, COUNT(*) FROM content_plan WHERE user_id = ? GROUP BY status', (user_id,))
    result = dict(cursor.fetchall())
    conn.close()
    return result


# === МЕДИА-БИБЛИОТЕКА (веб-кабинет) ===

def save_media(user_id, prompt, style, filename):
    """Сохраняет запись о сгенерированной картинке. Возвращает id записи."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO media (user_id, prompt, style, filename) VALUES (?, ?, ?, ?)',
        (user_id, prompt, style, filename)
    )
    conn.commit()
    media_id = cursor.lastrowid
    conn.close()
    return media_id


def get_media_for_user(user_id, limit=50):
    conn = _row_conn()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, prompt, style, filename, created_at FROM media '
        'WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT ?',
        (user_id, limit)
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_media_by_id_for_user(media_id, user_id):
    conn = _row_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM media WHERE id = ? AND user_id = ?', (media_id, user_id))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_media_by_id(user_id, media_id):
    """Удаляет запись о картинке. Возвращает filename, чтобы удалить и сам файл."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT filename FROM media WHERE id = ? AND user_id = ?', (media_id, user_id))
    row = cursor.fetchone()
    if row:
        cursor.execute('DELETE FROM media WHERE id = ? AND user_id = ?', (media_id, user_id))
        conn.commit()
        conn.close()
        return row[0]
    conn.close()
    return None


# Создаем базу при первом импорте
create_db()