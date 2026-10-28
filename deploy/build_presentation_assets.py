"""Рендерит логотипы и иконки дизайн-системы в PNG для презентации (Chrome headless, прозрачный фон).

Запуск из корня проекта: python deploy/build_presentation_assets.py
Результат — deploy/presentation_images/brand/*.png; generate_presentation.py берёт их оттуда.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "cabinet_service" / "static" / "press"
OUT = Path(__file__).resolve().parent / "presentation_images" / "brand"
CHROME = next((p for p in (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "google-chrome", "chromium",
) if shutil.which(p) or Path(p).exists()), None)

# Иконки, которые нужны слайдам; цвет — токены brand и белый
ICONS = ["sparkle", "image", "calendar", "megaphone", "persona", "chat", "chart", "link", "news", "grid",
         "download", "clock", "users", "building", "user", "check", "edit", "refresh", "key", "alert", "settings"]
COLORS = {"brand": "#1d71b8", "white": "#ffffff", "secondary": "#46566c"}


def ui_module():
    """Макросы _ui.html (логотип, знак, иконки) — те же, что в кабинете."""
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(str(ROOT / "cabinet_service" / "templates")))
    return env.get_template("_ui.html").module


def page(body, w, h):
    css = (STATIC / "tokens.css").as_uri(), (STATIC / "components.css").as_uri()
    return f"""<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="{css[0]}"><link rel="stylesheet" href="{css[1]}">
<style>html,body{{margin:0;background:transparent}} body{{width:{w}px;height:{h}px;display:flex;align-items:center;justify-content:flex-start;overflow:hidden}}</style>
</head><body>{body}</body></html>"""


def shot(html, w, h, name, tmp):
    src = Path(tmp) / f"{name}.html"
    src.write_text(html, encoding="utf-8")
    out = OUT / f"{name}.png"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--default-background-color=00000000", f"--window-size={w},{h}", "--virtual-time-budget=3000",
                    f"--screenshot={out}", src.as_uri()], check=True, capture_output=True, timeout=60)
    return out


def trim(path):
    """Обрезает прозрачные поля, чтобы картинку можно было ставить по точным координатам."""
    from PIL import Image
    im = Image.open(path)
    box = im.getbbox()
    if box:
        im.crop(box).save(path)


def main():
    if not CHROME:
        sys.exit("Нужен Chrome или Edge")
    OUT.mkdir(parents=True, exist_ok=True)
    ui = ui_module()
    with tempfile.TemporaryDirectory() as tmp:
        # Логотип с надписью: цветной (на светлом) и белый (на градиенте); знак 160px — запас для печати
        for tone in ("color", "white"):
            shot(page(str(ui.logo("lk" + tone, tone, 160)), 1400, 220), 1400, 220, f"lockup-{tone}", tmp)
            trim(OUT / f"lockup-{tone}.png")
        # Знак: цветная иконка с плашкой и белый знак без плашки
        shot(page(str(ui.mark("mkc", "color", 800)), 800, 800), 800, 800, "mark-color", tmp)
        shot(page(f'<span style="color:#fff">{ui.mark("mkw", "white", 800)}</span>', 800, 800), 800, 800, "mark-white", tmp)
        for n in ("mark-color", "mark-white"):
            trim(OUT / f"{n}.png")
        # Иконки 24px-сетки, рендер 192px
        for name in ICONS:
            for cname, color in COLORS.items():
                svg = str(ui.icon(name, 192)).replace('stroke-width="1.75"', 'stroke-width="1.75" style="color:%s"' % color)
                shot(page(svg, 192, 192), 192, 192, f"icon-{name}-{cname}", tmp)
    print("Готово:", len(list(OUT.glob("*.png"))), "файлов в", OUT)


if __name__ == "__main__":
    main()
