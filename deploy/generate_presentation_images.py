"""Генерация изображений для презентации через PiAPI."""
import sys
from pathlib import Path

from ai_core.image_generator import ImageGenerator

OUT_DIR = Path(__file__).resolve().parent / "presentation_images"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Промпты для изображений презентации
IMAGES = [
    {
        "name": "title_robot.png",
        "size": "square",
        "prompt": (
            "Friendly modern robot assistant character with a warm smile, "
            "wearing a professional suit, holding a smartphone showing a Telegram app. "
            "Surrounded by floating social media elements: a calendar, a chat bubble, "
            "a megaphone, a pencil, a lightbulb. Dark navy blue background (#0f172a) "
            "with soft blue gradient accents (#60a5fa). Clean, minimal, high-tech "
            "corporate style, flat vector illustration, bold shapes, no text, no letters."
        ),
    },
    {
        "name": "solution.png",
        "size": "wide",
        "prompt": (
            "Modern flat vector illustration of an AI assistant solving content creation "
            "tasks. A robot character at a desk with a laptop, generating posts, images "
            "and a content calendar. Floating icons: pencil, image, calendar, megaphone. "
            "Dark navy blue background (#0f172a) with blue accents (#60a5fa). "
            "Clean minimal corporate style, no text, no letters."
        ),
    },
    {
        "name": "media_brand.png",
        "size": "wide",
        "prompt": (
            "Modern flat vector illustration of brand identity and media image creation. "
            "A robot character building a brand book with color swatches, typography samples "
            "and style boards. Floating elements: paint palette, color swatches, document, "
            "target icon. Dark navy blue background (#0f172a) with blue accents (#60a5fa). "
            "Clean minimal corporate style, no text, no letters."
        ),
    },
]


def main():
    gen = ImageGenerator()
    for img in IMAGES:
        out = OUT_DIR / img["name"]
        print(f"Генерация {img['name']} ({img['size']})...")
        try:
            data = gen.generate(img["prompt"], size=img["size"])
            out.write_bytes(data)
            print(f"  ✅ {out} ({len(data)} байт)")
        except Exception as e:
            print(f"  ❌ Ошибка: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
