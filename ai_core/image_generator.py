import base64
import struct

import requests

from config import PIAPI_API_KEY, PIAPI_IMAGE_MODEL, get_proxies

PIAPI_IMAGE_URL = "https://api.piapi.ai/v1/images/generations"

# Размеры по моделям
# gpt-image-1: 1024x1024, 1536x1024, 1024x1536
# dall-e-3:    1024x1024, 1792x1024, 1024x1792
_MODEL_SIZES = {
    "gpt-image-1": {
        "square": ("1024x1024", "Квадрат 1024×1024"),
        "wide": ("1536x1024", "Горизонтальный 1536×1024"),
        "tall": ("1024x1536", "Вертикальный 1024×1536"),
    },
    "dall-e-3": {
        "square": ("1024x1024", "Квадрат 1024×1024"),
        "wide": ("1792x1024", "Горизонтальный 1792×1024"),
        "tall": ("1024x1792", "Вертикальный 1024×1792"),
    },
}

# Размеры по умолчанию (для неизвестных моделей — как у gpt-image-1)
DEFAULT_SIZES = {
    "square": ("1024x1024", "Квадрат 1024×1024"),
    "wide": ("1536x1024", "Горизонтальный 1536×1024"),
    "tall": ("1024x1536", "Вертикальный 1024×1536"),
}

# Обратная совместимость: IMAGE_SIZES для шаблонов
IMAGE_SIZES = DEFAULT_SIZES

# Пресеты стилей - дописываются к промпту
STYLE_PRESETS = {
    "none": ("Без стиля", ""),
    "photo": ("Фотореализм", ", ultra realistic photo, professional photography, natural lighting"),
    "illustration": ("Иллюстрация", ", digital illustration, vibrant colors, detailed"),
    "minimal": ("Минимализм", ", minimalist style, clean background, simple composition"),
    "3d": ("3D-рендер", ", 3D render, soft shadows, modern design"),
    "flat": ("Плоская графика", ", flat vector illustration, bold shapes, social media style"),
}

# Шаблоны изображений — готовые пресеты для быстрой генерации
# prompt — для свободной генерации (подставляется в textarea)
# prompt_template — для генерации к посту ({post_text} заменяется на текст поста)
IMAGE_TEMPLATES = [
    {
        "key": "product",
        "name": "Товар",
        "icon": "🛍️",
        "prompt": "Professional product photo on a clean studio background, soft gradient lighting, high-end commercial photography",
        "prompt_template": "Professional product photo on a clean studio background, soft gradient lighting, high-end commercial photography. Product related to: {post_text}",
        "style": "photo",
        "size": "square",
        "hint": "Фото товара на чистом фоне — для карточек и каталогов",
    },
    {
        "key": "lifestyle",
        "name": "Лайфстайл",
        "icon": "📸",
        "prompt": "Natural lifestyle scene, warm tones, candid feel, natural light, everyday setting",
        "prompt_template": "Natural lifestyle scene related to: {post_text}. A person in a cozy everyday setting, warm tones, candid feel, natural light",
        "style": "photo",
        "size": "wide",
        "hint": "Живая сцена из жизни — для постов и сторис",
    },
    {
        "key": "food",
        "name": "Еда",
        "icon": "🍕",
        "prompt": "Beautiful food photography, overhead flat lay or 45-degree angle, garnished plate, rustic wooden table, soft natural light, appetizing colors",
        "prompt_template": "Beautiful food photography of {post_text}, overhead flat lay or 45-degree angle, garnished plate, rustic wooden table, soft natural light, appetizing colors",
        "style": "photo",
        "size": "square",
        "hint": "Вкусная еда — для кафе, ресторанов, рецептов",
    },
    {
        "key": "business",
        "name": "Бизнес",
        "icon": "🏢",
        "prompt": "Professional business setting, modern office or meeting room, people in smart casual clothing, clean and bright atmosphere",
        "prompt_template": "Professional business setting illustrating: {post_text}. Modern office, people in smart casual, clean bright atmosphere",
        "style": "photo",
        "size": "wide",
        "hint": "Деловая атмосфера — для LinkedIn и презентаций",
    },
    {
        "key": "abstract",
        "name": "Абстрактный фон",
        "icon": "🎨",
        "prompt": "Abstract gradient background with flowing organic shapes, vibrant modern color palette, smooth transitions, depth effect",
        "prompt_template": "Abstract gradient background with flowing organic shapes and stylized text overlay reading: {post_text}. Vibrant modern color palette, smooth transitions, depth effect",
        "style": "none",
        "size": "square",
        "hint": "Красивый фон — для цитат, анонсов, обложек",
    },
    {
        "key": "portrait",
        "name": "Портрет",
        "icon": "👤",
        "prompt": "Professional portrait photo, soft studio lighting, blurred background, sharp focus on face, natural skin tones, confident expression",
        "prompt_template": "Professional portrait photo of a person who {post_text}. Soft studio lighting, blurred background, sharp focus, natural skin tones, confident expression",
        "style": "photo",
        "size": "square",
        "hint": "Портрет или аватар — для профилей и «О нас»",
    },
    {
        "key": "infographic",
        "name": "Инфографика",
        "icon": "📊",
        "prompt": "Clean infographic layout with icons, charts, and data visualization on white background, modern flat design, bold readable typography",
        "prompt_template": "Clean infographic design with the following text and data clearly rendered on it: {post_text}. White background, modern flat design, icons and charts, bold readable typography — the text from the post MUST be visible and legible on the image",
        "style": "flat",
        "size": "tall",
        "hint": "Визуализация данных — для статистик и гайдов",
    },
    {
        "key": "banner",
        "name": "Рекламный баннер",
        "icon": "🎯",
        "prompt": "Eye-catching advertising banner with bold typography, vibrant colors, modern promotional design, call to action",
        "prompt_template": "Eye-catching advertising banner with the following text prominently displayed: {post_text}. Vibrant colors, modern promotional design, the text must be the main focus of the image, bold readable typography",
        "style": "none",
        "size": "wide",
        "hint": "Баннер для рекламы — с текстом поста",
    },
    {
        "key": "nature",
        "name": "Природа",
        "icon": "🌄",
        "prompt": "Breathtaking nature landscape, golden hour lighting, vivid colors, dramatic sky, professional landscape photography",
        "prompt_template": "Breathtaking nature landscape illustrating the theme: {post_text}. Golden hour lighting, vivid colors, dramatic sky, professional landscape photography",
        "style": "photo",
        "size": "wide",
        "hint": "Пейзажи и природа — для мотивации и фона",
    },
    {
        "key": "minimal",
        "name": "Минимализм",
        "icon": "✨",
        "prompt": "Minimalist composition, single focal point, lots of white space, clean geometric shapes, soft muted colors, elegant simplicity",
        "prompt_template": "Minimalist design with the following text as the centerpiece: {post_text}. Clean white background, elegant typography, lots of breathing space, soft muted accent color",
        "style": "minimal",
        "size": "square",
        "hint": "Чистый минимализм — для премиальных брендов",
    },
    {
        "key": "story",
        "name": "Сторис",
        "icon": "📱",
        "prompt": "Vertical social media story, gradient background, centered composition, modern aesthetic, bold colors",
        "prompt_template": "Vertical social media story with the following text as the main element: {post_text}. Gradient background, centered composition, modern aesthetic, bold colors, the text must be clearly readable",
        "style": "none",
        "size": "tall",
        "hint": "Вертикальный формат — для Instagram/TikTok сторис",
    },
    {
        "key": "before_after",
        "name": "До / После",
        "icon": "🔄",
        "prompt": "Split composition before/after comparison, left side 'before', right side 'after', clean dividing line, matching lighting",
        "prompt_template": "Split composition before/after comparison related to: {post_text}. Left side shows 'before' state, right side shows 'after' transformation, clean dividing line, matching lighting",
        "style": "photo",
        "size": "wide",
        "hint": "Сравнение до/после — для кейсов и результатов",
    },
]


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


def get_sizes_for_model(model: str) -> dict:
    """Возвращает доступные размеры для конкретной модели."""
    if not model:
        return DEFAULT_SIZES
    # Точное совпадение
    if model in _MODEL_SIZES:
        return _MODEL_SIZES[model]
    # Частичное совпадение (напр. openai/dall-e-3)
    for key, sizes in _MODEL_SIZES.items():
        if key in model:
            return sizes
    return DEFAULT_SIZES


class ImageGenerator:
    """Генерация изображений через OpenAI-совместимый /images/generations."""

    def __init__(self, model=None, provider_settings=None):
        """provider_settings — опциональный dict:
          api_key, base_url, image_model
        Если не передан — используются глобальные настройки PiAPI."""
        if provider_settings and provider_settings.get("api_key"):
            self.api_key = provider_settings["api_key"]
            base = provider_settings.get("base_url") or "https://api.piapi.ai/v1"
            self.image_url = base.rstrip("/") + "/images/generations"
            self.model = model or provider_settings.get("image_model") or PIAPI_IMAGE_MODEL
            self.provider_type = provider_settings.get("provider_type", "custom")
            # Прокси для всех провайдеров (доступ из России к зарубежным API)
            self.proxies = get_proxies()
        else:
            self.api_key = PIAPI_API_KEY
            self.image_url = PIAPI_IMAGE_URL
            self.model = model or PIAPI_IMAGE_MODEL
            self.provider_type = "piapi"
            self.proxies = get_proxies()

    def generate(self, prompt: str, size: str = "square") -> bytes:
        """Генерирует картинку и возвращает её байты. Поднимает исключение при ошибке."""
        sizes = get_sizes_for_model(self.model)
        if size not in sizes:
            size = "square"
        size_value = sizes[size][0]

        # DALL-E 3 больше не поддерживается OpenAI — используем gpt-image-1
        # response_format и quality не передаём (gpt-image-1 возвращает b64_json по умолчанию)
        response = requests.post(
            self.image_url,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
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

    def generate_with_reference(self, prompt: str, reference_image_bytes: bytes, size: str = "square", chat_settings=None) -> bytes:
        """Генерирует изображение на основе промпта + исходного изображения.
        Пробует: 1) text-провайдер chat/completions, 2) image-провайдер chat/completions, 3) fallback без картинки.
        """
        sizes = get_sizes_for_model(self.model)
        if size not in sizes:
            size = "square"
        size_value = sizes[size][0]

        # Кодируем исходное изображение в base64
        img_b64 = base64.b64encode(reference_image_bytes).decode("utf-8")
        mime = "image/png"
        if reference_image_bytes[:2] == b"\xff\xd8":
            mime = "image/jpeg"
        elif reference_image_bytes[:4] == b"RIFF":
            mime = "image/webp"

        # Список провайдеров для попытки chat/completions с image input
        candidates = []
        if chat_settings and chat_settings.get("api_key"):
            candidates.append((chat_settings["api_key"], chat_settings.get("base_url", "https://api.openai.com/v1"), "text"))
        # image-провайдер тоже может уметь chat/completions (PiAPI/OpenAI)
        if self.api_key and (not chat_settings or self.api_key != chat_settings.get("api_key")):
            candidates.append((self.api_key, self.image_url.rsplit("/images/generations", 1)[0], "image"))
        # Fallback: default OpenAI
        if not candidates:
            candidates.append((self.api_key, "https://api.openai.com/v1", "default"))

        last_error = None
        for api_key, base_url, label in candidates:
            chat_url = base_url.rstrip("/") + "/chat/completions"
            print(f"[ImageGenerator] reference image -> {label} provider: {chat_url}")
            try:
                response = requests.post(
                    chat_url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"data:{mime};base64,{img_b64}"}
                                    }
                                ]
                            }
                        ],
                        "max_tokens": 4096,
                    },
                    proxies=self.proxies,
                    timeout=240,
                )
                if response.status_code >= 400:
                    last_error = f"{response.status_code} {response.reason}"
                    print(f"[ImageGenerator] {label} провайдер вернул {last_error}, пробуем следующий")
                    continue

                resp_json = response.json()
                msg = resp_json.get("choices", [{}])[0].get("message", {})
                content = msg.get("content", "")

                # Парсим картинку из ответа
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "image_url":
                            url = part.get("image_url", {}).get("url", "")
                            if url.startswith("data:"):
                                return base64.b64decode(url.split(",", 1)[1])
                if isinstance(content, str) and len(content) > 1000:
                    try:
                        return base64.b64decode(content)
                    except Exception:
                        pass

                print(f"[ImageGenerator] {label} провайдер не вернул картинку")
                last_error = "no image in response"
            except Exception as e:
                last_error = str(e)
                print(f"[ImageGenerator] {label} провайдер ошибка: {last_error}")

        # Все провайдеры не сработали — fallback без картинки
        print(f"[ImageGenerator] ни один провайдер не поддержал image input, генерируем без референса")
        return self.generate(prompt, size)
