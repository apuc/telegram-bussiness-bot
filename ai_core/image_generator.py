import base64
import struct

import requests

from config import PIAPI_API_KEY, PIAPI_IMAGE_MODEL, get_proxies

PIAPI_IMAGE_URL = "https://api.piapi.ai/v1/images/generations"

# Доступные размеры (gpt-image-1)
IMAGE_SIZES = {
    "square": ("1024x1024", "Квадрат 1024x1024"),
    "wide": ("1536x1024", "Горизонтальный 1536x1024"),
    "tall": ("1024x1536", "Вертикальный 1024x1536"),
}

# Пресеты стилей - дописываются к промпту
STYLE_PRESETS = {
    "none": ("Без стиля", ""),
    "photo": ("Фотореализм", ", ultra realistic photo, professional photography, natural lighting"),
    "illustration": ("Иллюстрация", ", digital illustration, vibrant colors, detailed"),
    "minimal": ("Минимализм", ", minimalist style, clean background, simple composition"),
    "3d": ("3D-рендер", ", 3D render, soft shadows, modern design"),
    "flat": ("Плоская графика", ", flat vector illustration, bold shapes, social media style"),
}


def detect_ext(data: bytes) -> str:
    """Определяет расширение файла по magic-байтам."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if data[:2] == b"\xff\xd8":
        return ".jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[:4] == b"GIF8":
        return ".gif"
    return ".png"


class ImageGenerator:
    """Генерация изображений через PiAPI (OpenAI-совместимый /images/generations)."""

    def __init__(self, model: str | None = None):
        self.model = model or PIAPI_IMAGE_MODEL
        self.proxies = get_proxies()

    def generate(self, prompt: str, size: str = "square") -> bytes:
        """Генерирует картинку и возвращает её байты. Поднимает исключение при ошибке."""
        if size not in IMAGE_SIZES:
            size = "square"
        size_value = IMAGE_SIZES[size][0]

        response = requests.post(
            PIAPI_IMAGE_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {PIAPI_API_KEY}",
            },
            json={
                "model": self.model,
                "prompt": prompt,
                "n": 1,
                "size": size_value,
            },
            proxies=self.proxies,
            timeout=240,
        )
        response.raise_for_status()

        data = response.json().get("data") or []
        if not data:
            raise RuntimeError("Пустой ответ от API картинок")

        item = data[0]
        if item.get("b64_json"):
            return base64.b64decode(item["b64_json"])
        if item.get("url"):
            img_response = requests.get(item["url"], proxies=self.proxies, timeout=120)
            img_response.raise_for_status()
            return img_response.content

        raise RuntimeError("Неожиданный формат ответа от API картинок")

    def build_prompt(self, prompt: str, style: str = "none") -> str:
        """Дополняет промпт пресетом стиля."""
        if style in STYLE_PRESETS:
            return prompt.strip() + STYLE_PRESETS[style][1]
        return prompt.strip()
