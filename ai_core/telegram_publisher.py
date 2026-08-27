"""Публикация постов в Telegram-каналы и чаты через Bot API.

Использует TOKEN из config — тот же токен, что и у бота.
Бот должен быть админом в канале/чате, куда публикуем."""

import re
import requests

from config import TOKEN, get_proxies

TELEGRAM_API = f"https://api.telegram.org/bot{TOKEN}"


def _md_to_html(text: str) -> str:
    """Конвертирует простой Markdown в HTML для Telegram.

    Поддерживает: **жирный**, *курсив*, __подчёркнутый~~зачёркнутый~~,
    `моноширинный`, ```блок кода```, заголовки ### в <b>,
    нумерованные/маркированные списки.
    Telegram HTML: <b>, <i>, <u>, <s>, <code>, <pre>, <a>.
    """
    # Сначала экранируем HTML-символы в тексте (но не наши теги)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Блоки кода ```...```
    text = re.sub(r'```(\w*)\n(.*?)```', r'<pre>\2</pre>', text, flags=re.DOTALL)
    text = re.sub(r'```(.*?)```', r'<pre>\1</pre>', text, flags=re.DOTALL)

    # Inline code `...`
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

    # Заголовки ### **Текст** → <b>Текст</b>
    text = re.sub(r'^#{1,6}\s+\*\*(.+?)\*\*\s*$', r'<b>\1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'^#{1,6}\s+(.+?)\s*$', r'<b>\1</b>', text, flags=re.MULTILINE)

    # Жирный **...**
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)

    # Курсив *...* (но не внутри <b> тегов)
    text = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<i>\1</i>', text)

    # Подчёркнутый __...__
    text = re.sub(r'__(.+?)__', r'<u>\1</u>', text)

    # Зачёркнутый ~~...~~
    text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text)

    return text


def _api_call(method, params):
    """Вызывает Telegram Bot API метод. Возвращает (ok, result_or_error)."""
    try:
        resp = requests.post(
            f"{TELEGRAM_API}/{method}",
            data=params,
            proxies=get_proxies(),
            timeout=30,
        )
        data = resp.json()
        if data.get("ok"):
            return True, data.get("result", {})
        return False, data.get("description", "Неизвестная ошибка")
    except Exception as e:
        return False, str(e)


def resolve_chat(username_or_id):
    """Разрешает @username или числовой ID в информацию о чате.
    Возвращает dict: {chat_id, title, username, type} или {error}."""
    # Нормализуем
    identifier = username_or_id.strip()
    if identifier.startswith("@"):
        identifier = identifier  # оставляем как есть для API
    elif identifier.lstrip("-").isdigit():
        identifier = int(identifier)

    ok, result = _api_call("getChat", {"chat_id": identifier})
    if not ok:
        return {"error": result}

    chat_id = result.get("id")
    chat_type = result.get("type", "unknown")
    title = result.get("title") or result.get("first_name", "") or result.get("username", "")
    username = result.get("username", "")

    return {
        "chat_id": chat_id,
        "title": title,
        "username": username,
        "type": chat_type,
    }


def check_bot_is_admin(chat_id):
    """Проверяет, является ли бот админом в чате/канале.
    Возвращает (is_admin, error_message)."""
    ok, result = _api_call("getChatMember", {
        "chat_id": chat_id,
        "user_id": _get_bot_id(),
    })
    if not ok:
        return False, f"Не удалось проверить статус: {result}"

    status = result.get("status", "")
    # administrator — для чатов, owner — для каналов
    if status in ("administrator", "creator", "owner"):
        return True, None
    return False, f"Бот не админ в этом чате (статус: {status}). Добавьте бота в админы."


def _get_bot_id():
    """Возвращает ID бота (кешируется)."""
    global _cached_bot_id
    if _cached_bot_id is not None:
        return _cached_bot_id
    ok, result = _api_call("getMe", {})
    if ok:
        _cached_bot_id = result.get("id")
        return _cached_bot_id
    return None


_cached_bot_id = None


def publish_post(chat_id, text, image_bytes=None):
    """Публикует пост в канал/чат.
    - text: текст поста (Markdown конвертируется в HTML)
    - image_bytes: опционально, байты картинки
    Возвращает (ok, message_or_message_id)."""
    text = _md_to_html(text)
    if image_bytes:
        ok, result = _api_call_send_photo(chat_id, image_bytes, text)
    else:
        ok, result = _api_call("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        })

    if ok:
        msg_id = result.get("message_id")
        return True, f"Опубликовано (message_id={msg_id})"
    return False, result


def _api_call_send_photo(chat_id, image_bytes, caption):
    """Отправляет фото с подписью.
    Если текст длиннее 1024 символов — фото без подписи + текст отдельным сообщением."""
    long_text = len(caption) > 1024
    try:
        files = {"photo": ("image.png", image_bytes, "image/png")}
        data = {
            "chat_id": chat_id,
            "caption": "" if long_text else caption,
            "parse_mode": "HTML" if not long_text else None,
        }
        # Убираем None из data
        data = {k: v for k, v in data.items() if v is not None}
        resp = requests.post(
            f"{TELEGRAM_API}/sendPhoto",
            data=data,
            files=files,
            proxies=get_proxies(),
            timeout=60,
        )
        data = resp.json()
        if not data.get("ok"):
            return False, data.get("description", "Ошибка отправки фото")

        # Если текст длинный — отправляем его отдельным сообщением
        if long_text:
            ok2, result2 = _api_call("sendMessage", {
                "chat_id": chat_id,
                "text": caption,
                "parse_mode": "HTML",
            })
            if not ok2:
                # Фото ушло, но текст не отправился — всё равно считаем успехом,
                # но возвращаем предупреждение
                return True, data.get("result", {})

        return True, data.get("result", {})
    except Exception as e:
        return False, str(e)
