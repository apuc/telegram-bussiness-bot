"""Генерация картинки для OpenGraph (og:image) через PiAPI."""
import sys
from pathlib import Path

from ai_core.image_generator import ImageGenerator

# Промпт для og:image — отражает суть сервиса "ИИ Пресс-секретарь"
PROMPT = (
    "Modern professional social media marketing banner for an AI press secretary service. "
    "A sleek robot assistant character with a friendly smile, surrounded by floating elements: "
    "a calendar, a chat bubble, a megaphone, a pencil, and a smartphone showing a Telegram app. "
    "Dark navy blue background (#0f172a) with soft blue gradient accents (#60a5fa). "
    "Clean, minimal, high-tech corporate style, flat vector illustration, bold shapes, "
    "wide horizontal composition, no text, no letters, no words."
)

SIZE = "wide"  # 1536x1024 для gpt-image-1


def main():
    out_path = Path(__file__).resolve().parent.parent / "cabinet_service" / "static" / "og-image.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Генерация картинки ({SIZE})...")
    gen = ImageGenerator()
    try:
        data = gen.generate(PROMPT, size=SIZE)
    except Exception as e:
        print(f"❌ Ошибка генерации: {e}")
        sys.exit(1)

    out_path.write_bytes(data)
    print(f"✅ Картинка сохранена: {out_path} ({len(data)} байт)")


if __name__ == "__main__":
    main()
