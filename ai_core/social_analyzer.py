"""
Анализатор профилей соцсетей.
Определяет платформу по URL, извлекает посты, отправляет на AI-анализ
для заполнения полей медиа-образа.
"""

import re
import json
import requests
from config import get_proxies


# === Определение платформы ===

def detect_platform(url: str) -> dict:
    """Определяет платформу по URL.
    Возвращает {"platform": str, "channel": str, "fetchable": bool}
    """
    url = url.strip()

    # Telegram: t.me/channel_name или t.me/s/channel_name
    m = re.match(r'https?://t\.me/(?:s/)?([a-zA-Z0-9_]+)', url)
    if m:
        return {"platform": "telegram", "channel": m.group(1), "fetchable": True}

    # VK: vk.com/username or vk.ru/username
    m = re.match(r'https?://(?:vk\.com|vk\.ru)/([a-zA-Z0-9_.]+)', url)
    if m:
        return {"platform": "vk", "channel": m.group(1), "fetchable": False}

    # Tenchat: tenchat.ru/username
    m = re.match(r'https?://tenchat\.ru/([a-zA-Z0-9_]+)', url)
    if m:
        return {"platform": "tenchat", "channel": m.group(1), "fetchable": False}

    # Instagram
    m = re.match(r'https?://(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)/?', url)
    if m:
        return {"platform": "instagram", "channel": m.group(1), "fetchable": False}

    return {"platform": "unknown", "channel": url, "fetchable": False}


# === Парсинг Telegram ===

def fetch_telegram_posts(channel_name: str, limit: int = 20) -> list:
    """Загружает посты из публичного Telegram-канала через t.me/s/.
    Возвращает список {"text": str, "date": str}.
    """
    url = f"https://t.me/s/{channel_name}"
    proxies = get_proxies()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        r = requests.get(url, proxies=proxies, timeout=15, headers=headers)
        r.raise_for_status()
    except Exception as e:
        print(f"[SocialAnalyzer] Ошибка загрузки Telegram: {e}")
        return []

    html = r.text

    # Извлекаем тексты постов
    texts = re.findall(
        r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',
        html, re.DOTALL
    )

    # Извлекаем даты
    dates = re.findall(
        r'class="tgme_widget_message_date"[^>]*>.*?<time[^>]*datetime="([^"]*)"',
        html, re.DOTALL
    )

    posts = []
    for i, raw_text in enumerate(texts[:limit]):
        clean = re.sub(r'<[^>]+>', ' ', raw_text).strip()
        clean = re.sub(r'\s+', ' ', clean)
        if len(clean) > 10:  # Пропускаем служебные сообщения
            date = dates[i] if i < len(dates) else ""
            posts.append({"text": clean, "date": date})

    print(f"[SocialAnalyzer] Telegram: загружено {len(posts)} постов из @{channel_name}")
    return posts


# === AI-анализ постов ===

ANALYSIS_PROMPT_TEMPLATE = """
Ты — эксперт по брендингу и SMM. Проанализируй {count} постов из профиля/канала и извлеки параметры для медиа-образа.

=== ПОСТЫ ДЛЯ АНАЛИЗА ===
{posts_text}

=== ЗАДАЧА ===
Проанализируй стиль, тон, темы, подачу и структуру постов. Верни JSON со следующими полями:

{{
  "client_name": "Имя или название канала/профиля (если можно определить)",
  "brand_essence": "Сущность бренда одной строкой (что этот человек/бренд транслирует)",
  "tov_description": "Описание Tone of Voice (тон общения, манера подачи)",
  "tov_axes": "Оси ToV (по строкам, 3-5 шт)",
  "tov_references": "На кого/что похож стиль (референсы)",
  "prompt_directions": "Контент-направления (по строкам, какие темы затрагиваются)",
  "prompt_structure": "Типичная структура постов (как строются тексты)",
  "prompt_formats": "Типичные форматы постов (экспертный, личный, вовлекающий и т.д.)",
  "current_situation": "Краткое описание: кто этот человек/бренд, чем занимается",
  "client_role": "Роль / профессия (если определяется)",
  "positioning_who": "Для кого контент (целевая аудитория)",
  "positioning_problem": "Какую проблему решает",
  "positioning_result": "Какой результат получает аудитория"
}}

Верни ТОЛЬКО валидный JSON без markdown и пояснений.
"""


def analyze_posts_with_ai(posts: list, provider_settings: dict = None) -> dict:
    """Отправляет посты на AI-анализ и возвращает структурированные данные
    для заполнения медиа-образа.
    """
    if not posts:
        return {"error": "Нет постов для анализа"}

    # Склеиваем посты
    posts_text = ""
    for i, p in enumerate(posts[:20], 1):
        date_str = f" ({p['date']})" if p.get("date") else ""
        posts_text += f"\n--- Пост {i}{date_str} ---\n{p['text']}\n"

    prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        count=len(posts[:20]),
        posts_text=posts_text
    )

    # Определяем AI-провайдер
    if provider_settings and provider_settings.get("api_key"):
        api_key = provider_settings["api_key"]
        base_url = provider_settings.get("base_url", "https://api.piapi.ai/v1")
        model = provider_settings.get("text_model", "gpt-4o")
    else:
        from config import PIAPI_API_KEY, PIAPI_MODEL
        api_key = PIAPI_API_KEY
        base_url = "https://api.piapi.ai/v1"
        model = PIAPI_MODEL

    if not api_key:
        return {"error": "AI-провайдер не настроен. Настройте ИИ в разделе «ИИ»."}

    chat_url = base_url.rstrip("/") + "/chat/completions"
    proxies = get_proxies()

    try:
        response = requests.post(
            chat_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "Ты эксперт по брендингу. Отвечаешь только валидным JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 2000,
                "response_format": {"type": "json_object"}
            },
            proxies=proxies,
            timeout=90
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()

        # Парсим JSON
        result = json.loads(content)
        print(f"[SocialAnalyzer] AI-анализ завершён, получено {len(result)} полей")
        return result

    except json.JSONDecodeError as e:
        print(f"[SocialAnalyzer] Ошибка парсинга JSON от AI: {e}")
        return {"error": "AI вернул некорректный JSON. Попробуйте ещё раз."}
    except Exception as e:
        print(f"[SocialAnalyzer] Ошибка AI: {e}")
        return {"error": f"Ошибка AI: {e}"}
