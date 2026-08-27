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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS brand_surveys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            chat_id TEXT,
            title TEXT,
            username TEXT,
            chat_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS provider_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            text_provider_type TEXT DEFAULT 'piapi',
            text_api_key TEXT,
            text_base_url TEXT,
            text_model TEXT,
            image_provider_type TEXT DEFAULT 'piapi',
            image_api_key TEXT,
            image_base_url TEXT,
            image_model TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS post_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            user_id INTEGER,
            filename TEXT,
            source TEXT DEFAULT 'upload',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_type TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            result_json TEXT,
            error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS post_revisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
        )
    ''')

    # Миграция со старой схемы (provider_type/api_key/base_url/text_model/image_model)
    # на новую (text_* + image_*). Если старых колонок нет — пропускаем.
    cursor.execute("PRAGMA table_info(provider_settings)")
    ps_columns = [row[1] for row in cursor.fetchall()]
    if 'provider_type' in ps_columns and 'text_provider_type' in ps_columns:
        # Промежуточное состояние миграции — копируем данные из старых колонок в новые
        try:
            cursor.execute('''
                UPDATE provider_settings SET
                    text_provider_type = COALESCE(text_provider_type, provider_type),
                    text_api_key = COALESCE(text_api_key, api_key),
                    text_base_url = COALESCE(text_base_url, base_url),
                    image_provider_type = COALESCE(image_provider_type, provider_type),
                    image_api_key = COALESCE(image_api_key, api_key),
                    image_base_url = COALESCE(image_base_url, base_url),
                    image_model = COALESCE(image_model, image_model)
                WHERE api_key IS NOT NULL
            ''')
        except Exception:
            pass

    # Колонка published в posts
    cursor.execute("PRAGMA table_info(posts)")
    posts_columns = [row[1] for row in cursor.fetchall()]
    if 'published' not in posts_columns:
        cursor.execute('ALTER TABLE posts ADD COLUMN published BOOLEAN DEFAULT 0')
        print("✅ Колонка 'published' добавлена в таблицу posts")
    if 'published_at' not in posts_columns:
        cursor.execute('ALTER TABLE posts ADD COLUMN published_at TIMESTAMP')
        print("✅ Колонка 'published_at' добавлена в таблицу posts")
    if 'published_to' not in posts_columns:
        cursor.execute('ALTER TABLE posts ADD COLUMN published_to TEXT')
        print("✅ Колонка 'published_to' добавлена в таблицу posts")

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


def create_web_user(email, password_hash, name, phone, business_type=None, description=None):
    """Создаёт пользователя веб-кабинета (без telegram_id).
    business_type и description опциональны — посты генерируются на основе медиа-образа.
    Возвращает id нового пользователя."""
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
    post_id = cursor.lastrowid
    # Сохраняем начальную ревизию
    cursor.execute(
        'INSERT INTO post_revisions (post_id, user_id, content) VALUES (?, ?, ?)',
        (post_id, user_id, content),
    )
    conn.commit()
    conn.close()
    return post_id


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


# === РЕВИЗИИ ПОСТОВ ===

def add_post_revision(post_id, user_id, content):
    """Сохраняет ревизию (каждое изменение текста поста)."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO post_revisions (post_id, user_id, content) VALUES (?, ?, ?)',
        (post_id, user_id, content),
    )
    conn.commit()
    conn.close()


def get_post_revisions(post_id, user_id, limit=50):
    """Возвращает последние N ревизий поста (от новых к старым)."""
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, content, created_at FROM post_revisions '
        'WHERE post_id = ? AND user_id = ? ORDER BY id DESC LIMIT ?',
        (post_id, user_id, limit),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


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


# === ОПРОСЫ МЕДИА-ОБРАЗА (веб-кабинет) ===

import json as _json


def save_brand_survey(user_id, title, data):
    """Сохраняет опрос медиа-образа. data — dict (сериализуется в JSON).
    Возвращает id новой записи."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO brand_surveys (user_id, title, data) VALUES (?, ?, ?)',
        (user_id, title, _json.dumps(data, ensure_ascii=False))
    )
    conn.commit()
    survey_id = cursor.lastrowid
    conn.close()
    return survey_id


def get_brand_surveys_for_user(user_id, limit=50):
    """Возвращает список опросов пользователя (без поля data)."""
    conn = _row_conn()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, title, created_at FROM brand_surveys '
        'WHERE user_id = ? ORDER BY created_at DESC LIMIT ?',
        (user_id, limit)
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_latest_brand_survey_for_user(user_id):
    """Возвращает последний опрос медиа-образа пользователя (с data) или None."""
    conn = _row_conn()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM brand_surveys WHERE user_id = ? ORDER BY created_at DESC LIMIT 1',
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    result = dict(row)
    result['data'] = _json.loads(result['data']) if result['data'] else {}
    return result


def get_brand_survey_by_id(survey_id, user_id):
    """Возвращает один опрос (с data) только если он принадлежит user_id."""
    conn = _row_conn()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM brand_surveys WHERE id = ? AND user_id = ?',
        (survey_id, user_id)
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    result = dict(row)
    result['data'] = _json.loads(result['data']) if result['data'] else {}
    return result


def delete_brand_survey(user_id, survey_id):
    """Удаляет опрос. Только если он принадлежит user_id."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM brand_surveys WHERE id = ? AND user_id = ?',
        (survey_id, user_id)
    )
    conn.commit()
    conn.close()


# === КАНАЛЫ ДЛЯ ПУБЛИКАЦИИ (веб-кабинет) ===

def save_channel(user_id, chat_id, title, username, chat_type):
    """Сохраняет канал/чат для публикации. Возвращает id записи."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO channels (user_id, chat_id, title, username, chat_type) VALUES (?, ?, ?, ?, ?)',
        (user_id, str(chat_id), title, username, chat_type)
    )
    conn.commit()
    channel_id = cursor.lastrowid
    conn.close()
    return channel_id


def get_channels_for_user(user_id):
    """Возвращает список каналов пользователя."""
    conn = _row_conn()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, chat_id, title, username, chat_type, created_at '
        'FROM channels WHERE user_id = ? ORDER BY created_at DESC',
        (user_id,)
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_channel_by_id(channel_id, user_id):
    """Возвращает один канал только если он принадлежит user_id."""
    conn = _row_conn()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM channels WHERE id = ? AND user_id = ?',
        (channel_id, user_id)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_channel(user_id, channel_id):
    """Удаляет канал. Только если он принадлежит user_id."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM channels WHERE id = ? AND user_id = ?',
        (channel_id, user_id)
    )
    conn.commit()
    conn.close()


def is_channel_already_added(user_id, chat_id):
    """Проверяет, добавлен ли уже канал с таким chat_id."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id FROM channels WHERE user_id = ? AND chat_id = ?',
        (user_id, str(chat_id))
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None


# === ОТМЕТКА О ПУБЛИКАЦИИ ПОСТА ===

def mark_post_published(post_id, user_id, channel_title):
    """Отмечает пост как опубликованный."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE posts SET published = 1, published_at = CURRENT_TIMESTAMP, '
        'published_to = ? WHERE id = ? AND user_id = ?',
        (channel_title, post_id, user_id)
    )
    conn.commit()
    conn.close()


# === НАСТРОЙКИ ПРОВАЙДЕРА ИИ (веб-кабинет) ===

# Пресеты провайдеров
PROVIDER_PRESETS = {
    'piapi': {
        'name': 'PiAPI',
        'base_url': 'https://api.piapi.ai/v1',
        'text_model': 'gpt-4o',
        'image_model': 'gpt-image-1',
        'needs_key': True,
        'supports_images': True,
    },
    'openrouter': {
        'name': 'OpenRouter',
        'base_url': 'https://openrouter.ai/api/v1',
        'text_model': 'openai/gpt-4o',
        'image_model': 'openai/dall-e-3',
        'needs_key': True,
        'supports_images': True,
    },
    'opencode': {
        'name': 'OpenCode Zen',
        'base_url': 'https://opencode.ai/zen/v1',
        'text_model': 'nemotron-3-ultra-free',
        'image_model': '',
        'needs_key': True,
        'supports_images': False,
    },
    'openai': {
        'name': 'OpenAI',
        'base_url': 'https://api.openai.com/v1',
        'text_model': 'gpt-4o',
        'image_model': 'gpt-image-1',
        'needs_key': True,
        'supports_images': True,
    },
    'custom': {
        'name': 'Кастомный (OpenAI-совместимый)',
        'base_url': '',
        'text_model': '',
        'image_model': '',
        'needs_key': True,
        'supports_images': True,
    },
}


def get_provider_settings(user_id):
    """Возвращает настройки провайдеров пользователя (text + image) или None."""
    conn = _row_conn()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT text_provider_type, text_api_key, text_base_url, text_model,
               image_provider_type, image_api_key, image_base_url, image_model,
               updated_at
        FROM provider_settings WHERE user_id = ?
    ''', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    return {
        # Text provider
        'text_provider_type': d['text_provider_type'],
        'text_api_key': d['text_api_key'],
        'text_base_url': d['text_base_url'],
        'text_model': d['text_model'],
        # Image provider
        'image_provider_type': d['image_provider_type'],
        'image_api_key': d['image_api_key'],
        'image_base_url': d['image_base_url'],
        'image_model': d['image_model'],
        # Meta
        'updated_at': d['updated_at'],
    }


def get_text_provider_settings(user_id):
    """Возвращает настройки только text-провайдера в формате для ContentGenerator."""
    s = get_provider_settings(user_id)
    if not s or not s.get('text_api_key'):
        return None
    return {
        'provider_type': s['text_provider_type'],
        'api_key': s['text_api_key'],
        'base_url': s['text_base_url'],
        'text_model': s['text_model'],
    }


def get_image_provider_settings(user_id):
    """Возвращает настройки только image-провайдера в формате для ImageGenerator."""
    s = get_provider_settings(user_id)
    if not s or not s.get('image_api_key'):
        return None
    return {
        'provider_type': s['image_provider_type'],
        'api_key': s['image_api_key'],
        'base_url': s['image_base_url'],
        'image_model': s['image_model'],
    }


def save_provider_settings(user_id, text_provider_type, text_api_key, text_base_url, text_model,
                            image_provider_type, image_api_key, image_base_url, image_model):
    """Сохраняет или обновляет настройки обоих провайдеров."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO provider_settings (
            user_id, text_provider_type, text_api_key, text_base_url, text_model,
            image_provider_type, image_api_key, image_base_url, image_model, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            text_provider_type = excluded.text_provider_type,
            text_api_key = excluded.text_api_key,
            text_base_url = excluded.text_base_url,
            text_model = excluded.text_model,
            image_provider_type = excluded.image_provider_type,
            image_api_key = excluded.image_api_key,
            image_base_url = excluded.image_base_url,
            image_model = excluded.image_model,
            updated_at = CURRENT_TIMESTAMP
    ''', (user_id, text_provider_type, text_api_key, text_base_url, text_model,
          image_provider_type, image_api_key, image_base_url, image_model))
    conn.commit()
    conn.close()


# === ИЗОБРАЖЕНИЯ ПОСТОВ (веб-кабинет) ===

def save_post_image(post_id, user_id, filename, source='upload'):
    """Сохраняет запись об изображении, прикреплённом к посту."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO post_images (post_id, user_id, filename, source) VALUES (?, ?, ?, ?)',
        (post_id, user_id, filename, source)
    )
    conn.commit()
    img_id = cursor.lastrowid
    conn.close()
    return img_id


def get_post_images(post_id, user_id):
    """Возвращает все изображения поста (только если пост принадлежит user_id)."""
    conn = _row_conn()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, filename, source, created_at FROM post_images '
        'WHERE post_id = ? AND user_id = ? ORDER BY created_at ASC',
        (post_id, user_id)
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def delete_post_image(image_id, user_id):
    """Удаляет изображение. Возвращает filename для удаления файла, или None."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT filename FROM post_images WHERE id = ? AND user_id = ?',
        (image_id, user_id)
    )
    row = cursor.fetchone()
    if row:
        cursor.execute('DELETE FROM post_images WHERE id = ? AND user_id = ?', (image_id, user_id))
        conn.commit()
        conn.close()
        return row[0]
    conn.close()
    return None


# === Задачи (background tasks) ===

def create_task(user_id, task_type):
    """Создаёт задачу. Возвращает task_id."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO tasks (user_id, task_type, status) VALUES (?, ?, ?)',
        (user_id, task_type, 'pending')
    )
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return task_id


def update_task_status(task_id, status, result_json=None, error=None):
    """Обновляет статус задачи."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE tasks SET status = ?, result_json = ?, error = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        (status, result_json, error, task_id)
    )
    conn.commit()
    conn.close()


def get_task(task_id):
    """Возвращает задачу по ID."""
    conn = _row_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# Создаем базу при первом импорте
create_db()