"""Презентация сервиса «ИИ Пресс-секретарь» — 10 слайдов 16:9 по брендбуку (дизайн-система «Жидкое стекло»).

Запуск из корня проекта:
    python deploy/build_presentation_assets.py   # логотипы и иконки из дизайн-системы (один раз)
    python deploy/generate_presentation.py       # PPTX в корне проекта

PDF и встраивание шрифта Donbass — через PowerPoint (см. export_presentation.ps1).
Нужны python-pptx и Pillow; шрифт Donbass должен быть установлен в системе.

Слайд рисуется на холсте 1280×720 px: координаты в px, 1 px = 9525 EMU. Ритм отступов — 8 px.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

HERE = Path(__file__).resolve().parent
IMG = HERE / "presentation_images"
BRAND = IMG / "brand"
SCREENS = IMG / "screens"
BUILD = IMG / "build"
OUT = HERE.parent / "ИИ_Пресс-секретарь_презентация.pptx"

W, H = 1280, 720
M = 64                  # поля слайда
TOTAL = 10


def hex_rgb(h):
    h = h.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# === Токены светлой темы (tokens.json) ===
T = {k: hex_rgb(v) for k, v in {
    "surface": "#f4f7fb", "raised": "#ffffff", "sunken": "#e9eff6", "hairline": "#d6e0ec",
    "ink": "#0e1b2e", "ink2": "#46566c", "ink3": "#5d6d84",
    "brand": "#1d71b8", "brand_bright": "#009fe3", "logo_deep": "#1d71b8", "logo_shade": "#312783",
    "brand_tint": "#e9f4fc", "indigo": "#312783", "indigo_tint": "#ecebfa",
    "success": "#0b7552", "success_tint": "#e1f3eb", "white": "#ffffff",
}.items()}

# Donbass: Regular/Bold — семейство «Donbass», полужирный и средний — отдельные семейства
F_REG, F_MED, F_SEMI, F_BOLD = "Donbass", "Donbass Medium", "Donbass SemiBold", "Donbass"


def px(v):
    return Emu(int(round(v * 9525)))


def fpx(v):
    """Кегль и интерлиньяж в px холста → pt (1280 px = 960 pt)."""
    return Pt(v * 0.75)


# === Растровые подложки (Pillow) ===

def _gradient(size, c1, c2, angle_down_left=True):
    """Линейный градиент бренда 200°: brand-bright сверху справа → logo-deep снизу слева."""
    w, h = size
    img = Image.new("RGB", size)
    a = Image.linear_gradient("L").resize((w, h))          # 0 сверху → 255 снизу
    b = Image.linear_gradient("L").rotate(90).resize((w, h))  # 0 справа → 255 слева
    mix = Image.blend(a, b, 0.36 if angle_down_left else 0)
    img = Image.composite(Image.new("RGB", size, c2), Image.new("RGB", size, c1), mix)
    return img


def _blob(base, xy, r, color, alpha):
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse([xy[0] - r, xy[1] - r, xy[0] + r, xy[1] + r], fill=color + (int(255 * alpha),))
    layer = layer.filter(ImageFilter.GaussianBlur(r * 0.45))
    base.alpha_composite(layer)


def build_backgrounds():
    BUILD.mkdir(parents=True, exist_ok=True)
    S = 2  # рендер в 2× — без ступенек на больших экранах
    # Контентные слайды: surface + пятна ambient-1..3, как фон кабинета
    bg = Image.new("RGBA", (W * S, H * S), (244, 247, 251, 255))
    _blob(bg, (80 * S, -40 * S), 420 * S, (0, 159, 227), 0.16)
    _blob(bg, (1240 * S, 40 * S), 380 * S, (49, 39, 131), 0.08)
    _blob(bg, (700 * S, 820 * S), 460 * S, (29, 113, 184), 0.10)
    bg.convert("RGB").save(BUILD / "bg-surface.png")

    # Обложка и финал: градиент бренда + белый знак целиком (без обрезки листов), 14% белого
    for name, mark_h, mark_x, mark_y in (("bg-cover", 440, 652, 140), ("bg-cta", 0, 0, 0)):
        g = _gradient((W * S, H * S), (0, 159, 227), (29, 113, 184)).convert("RGBA")
        _blob(g, (1180 * S, 120 * S), 360 * S, (255, 255, 255), 0.10)
        _blob(g, (120 * S, 760 * S), 420 * S, (49, 39, 131), 0.22)
        if mark_h:
            mark = Image.open(BRAND / "mark-white.png").convert("RGBA")
            mw = int(mark.width * mark_h * S / mark.height)
            mark = mark.resize((mw, mark_h * S), Image.LANCZOS)
            mark.putalpha(mark.getchannel("A").point(lambda v: int(v * 0.16)))
            g.alpha_composite(mark, (mark_x * S, mark_y * S))
        g.convert("RGB").save(BUILD / f"{name}.png")


def framed_screen(name, crop=None):
    """Скриншот кабинета в карточке: скругление radius-lg, рамка hairline, мягкая тень shadow-float."""
    src = Image.open(SCREENS / f"{name}.png").convert("RGB")
    if crop:
        src = src.crop(crop)
    w, h = src.size
    r = 44                       # 22 px × 2 (скриншот в 2×)
    pad = 80                     # место под тень
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255)
    out = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    shadow = Image.new("RGBA", out.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([pad, pad + 24, pad + w, pad + h + 24], r, fill=(14, 27, 46, 60))
    out.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(36)))
    card = src.convert("RGBA")
    card.putalpha(mask)
    out.alpha_composite(card, (pad, pad))
    ImageDraw.Draw(out).rounded_rectangle([pad, pad, pad + w - 1, pad + h - 1], r, outline=(214, 224, 236, 255), width=2)
    path = BUILD / f"screen-{name}.png"
    out.save(path)
    return path, pad, w


def screen(slide, name, x, y, w):
    """Ставит скриншот так, чтобы сама карточка (без поля тени) заняла x, y, w."""
    path, pad, src_w = framed_screen(name)
    k = w / src_w
    return picture(slide, path, x - pad * k, y - pad * k, w=w + 2 * pad * k)


# === Примитивы слайда ===

def picture(slide, path, x, y, w=None, h=None):
    im = Image.open(path)
    if w and not h:
        h = w * im.height / im.width
    elif h and not w:
        w = h * im.width / im.height
    return slide.shapes.add_picture(str(path), px(x), px(y), px(w), px(h))


def rect(slide, x, y, w, h, fill=None, line=None, radius=0, shape=None):
    kind = shape or (MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE)
    s = slide.shapes.add_shape(kind, px(x), px(y), px(w), px(h))
    if radius and kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = min(0.5, radius / min(w, h))
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(0.75)
    s.shadow.inherit = False
    s.text_frame.text = ""
    return s


def set_alpha(shape, alpha):
    """Прозрачность заливки (python-pptx не умеет напрямую)."""
    clr = shape.fill._xPr.find(qn("a:solidFill"))[0]
    el = clr.makeelement(qn("a:alpha"), {"val": str(int(alpha * 100000))})
    clr.append(el)


def text(slide, x, y, w, h, runs, size=15, color=None, font=F_REG, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, line=None, space_after=0, tracking=None):
    """runs — строка или список абзацев; абзац — строка или список (текст, {font, color, bold, size})."""
    box = slide.shapes.add_textbox(px(x), px(y), px(w), px(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    paras = runs if isinstance(runs, list) else [runs]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if line:
            p.line_spacing = fpx(line)
        if space_after and i < len(paras) - 1:
            p.space_after = fpx(space_after)
        for chunk in (para if isinstance(para, list) else [(para, {})]):
            t, o = chunk if isinstance(chunk, tuple) else (chunk, {})
            r = p.add_run()
            r.text = t
            r.font.size = fpx(o.get("size", size))
            r.font.name = o.get("font", font)
            r.font.bold = o.get("bold", bold)
            r.font.color.rgb = o.get("color", color or T["ink"])
            if tracking is not None:
                r.font._element.set("spc", str(int(tracking)))
    return box


def icon_tile(slide, x, y, name, size=44, tone="brand"):
    """Плитка иконки tile-lg: подложка brand-tint, радиус radius-sm, иконка 24 px."""
    fill = T["brand_tint"] if tone == "brand" else None
    t = rect(slide, x, y, size, size, fill=fill, radius=12)
    if tone == "glass":
        t.fill.solid(); t.fill.fore_color.rgb = T["white"]; set_alpha(t, 0.18)
    icon = size * 0.55
    picture(slide, BRAND / f"icon-{name}-{'brand' if tone == 'brand' else 'white'}.png",
            x + (size - icon) / 2, y + (size - icon) / 2, w=icon, h=icon)
    return t


def card(slide, x, y, w, h, fill=None):
    return rect(slide, x, y, w, h, fill=fill or T["raised"], line=T["hairline"], radius=22)


def content_slide(prs, num, title, lead=None):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    picture(s, BUILD / "bg-surface.png", 0, 0, W, H)
    picture(s, BRAND / "lockup-color.png", M, 36, h=26)
    text(s, W - M - 120, 40, 120, 20, f"{num:02d} / {TOTAL}", size=14, color=T["ink3"], font=F_MED,
         align=PP_ALIGN.RIGHT, tracking=40)
    text(s, M, 92, 1100, 52, title, size=40, font=F_BOLD, bold=True, line=48, tracking=-40)
    if lead:
        text(s, M, 148, 1000, 30, lead, size=20, color=T["ink2"], line=28)
    text(s, M, H - 48, 300, 20, "press.my-dpr.ru", size=14, color=T["ink3"], font=F_MED)
    return s


def bullet_list(slide, x, y, w, items, icon="check", gap=20, size=18, body_lines=1):
    """Строки с иконкой в круге brand-tint — вместо маркеров-точек."""
    cy = y
    for item in items:
        title, body = item if isinstance(item, tuple) else (item, None)
        rect(slide, x, cy, 28, 28, fill=T["brand_tint"], shape=MSO_SHAPE.OVAL)
        picture(slide, BRAND / f"icon-{icon}-brand.png", x + 6, cy + 6, w=16, h=16)
        paras = [[(title, {"font": F_SEMI, "color": T["ink"]})]]
        if body:
            paras.append([(body, {"color": T["ink2"], "size": 16})])
        hgt = 26 + (24 * body_lines if body else 0)
        text(slide, x + 44, cy + 1, w - 44, hgt, paras, size=size, line=24, space_after=2)
        cy += hgt + gap
    return cy


def pill(slide, x, y, w, label, fill, color, line=None, alpha=None, h=52):
    b = rect(slide, x, y, w, h, fill=fill, line=line, radius=h / 2)
    if alpha is not None:
        set_alpha(b, alpha)
    text(slide, x, y, w, h, label, size=18, font=F_SEMI, color=color, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    return b


# === Слайды ===

def build():
    build_backgrounds()
    prs = Presentation()
    prs.slide_width, prs.slide_height = px(W), px(H)
    blank = prs.slide_layouts[6]

    # 1. Обложка
    s = prs.slides.add_slide(blank)
    picture(s, BUILD / "bg-cover.png", 0, 0, W, H)
    picture(s, BRAND / "lockup-white.png", M, 48, h=32)
    text(s, M, 196, 680, 20, "ПРЕЗЕНТАЦИЯ СЕРВИСА", size=14, font=F_SEMI, color=T["white"], tracking=160)
    text(s, M, 228, 700, 230, "Пресс-секретарь, который говорит вашим голосом", size=68, font=F_BOLD, bold=True,
         color=T["white"], line=72, tracking=-50)
    text(s, M, 476, 640, 64, "Посты, картинки и контент-план по медиа-образу бренда. "
         "Публикация в Telegram — в один клик.", size=22, color=T["white"], line=32)
    pill(s, M, 584, 196, "press.my-dpr.ru", T["white"], T["white"], alpha=0.18, h=44)

    # 2. Проблема
    s = content_slide(prs, 2, "Соцсети отнимают слишком много времени",
                      "Регулярный контент нужен каждому бизнесу, но на него не хватает рук.")
    problems = [
        ("clock", "Нет времени", "Посты нужны каждый день, а у владельца бизнеса — десятки других задач."),
        ("edit", "Нет идей", "Придумывать новый пост каждый день сложно даже профессионалу."),
        ("users", "Дорогая команда", "Копирайтер и дизайнер в штате — расходы, которые малому бизнесу не по силам."),
        ("persona", "Разный стиль", "Без медиа-образа посты каждый раз звучат по-разному."),
        ("megaphone", "Ручная публикация", "Скопировать, вставить, приложить фото — рутина, которая съедает время."),
    ]
    cw, gap = (W - 2 * M - 4 * 16) / 5, 16
    for i, (ic, t, b) in enumerate(problems):
        x = M + i * (cw + gap)
        card(s, x, 232, cw, 312)
        icon_tile(s, x + 24, 256, ic)
        text(s, x + 24, 320, cw - 48, 56, t, size=22, font=F_SEMI, line=28)
        text(s, x + 24, 384, cw - 48, 160, b, size=16, color=T["ink2"], line=24)

    # 3. Решение
    s = content_slide(prs, 3, "ИИ Пресс-секретарь берёт контент на себя",
                      "Один кабинет вместо копирайтера, дизайнера и ручной публикации.")
    bullet_list(s, M, 208, 470, [
        ("Пишет посты", "Тексты для Telegram, Instagram, LinkedIn и TenChat."),
        ("Рисует картинки", "Иллюстрации к постам по 12 шаблонам или по концепции."),
        ("Планирует", "Контент-план на неделю или две — идея и платформа на каждый день."),
        ("Говорит вашим голосом", "Каждый результат сделан по медиа-образу бренда."),
        ("Публикует", "Пост уходит в ваш Telegram-канал по одной команде."),
    ], gap=12, body_lines=2)
    screen(s, "dashboard", 588, 208, 640)

    # 4. Возможности
    s = content_slide(prs, 4, "Всё для контента — в одном кабинете")
    feats = [
        ("sparkle", "Посты", "ИИ пишет пост по медиа-образу: платформа, стиль и пожелания — на ваш выбор. "
         "Правки — командами в чате."),
        ("image", "Картинки", "Иллюстрации без дизайнера и фотостока: 12 шаблонов, подбор концепции по тексту "
         "поста или ваш образец."),
        ("calendar", "Контент-план", "Идеи постов на каждый день. Из пункта плана — сразу в «Создать пост», "
         "статусы показывают, что уже вышло."),
        ("megaphone", "Публикация", "Подключите Telegram-каналы и публикуйте из кабинета. TenChat — тоже."),
    ]
    cw = (W - 2 * M - 3 * 16) / 4
    for i, (ic, t, b) in enumerate(feats):
        x = M + i * (cw + 16)
        card(s, x, 184, cw, 344)
        icon_tile(s, x + 28, 212, ic, size=52)
        text(s, x + 28, 292, cw - 56, 32, t, size=24, font=F_SEMI, line=30)
        text(s, x + 28, 336, cw - 56, 220, b, size=17, color=T["ink2"], line=25)
    # Метка «ИИ»: голос ассистента — indigo
    b = rect(s, M, 560, 680, 44, fill=T["indigo_tint"], radius=22)
    text(s, M + 20, 560, 660, 44, [[("ИИ  ", {"font": F_BOLD, "bold": True, "color": T["indigo"]}),
                                     ("пишет черновик — в канал пост уходит только по вашей команде", {"color": T["ink"]})]],
         size=16, anchor=MSO_ANCHOR.MIDDLE)

    # 5. Медиа-образ
    s = content_slide(prs, 5, "Медиа-образ — голос вашего бренда",
                      "Анкета, по которой ИИ пишет каждый пост: тон, УТП, аудитория, позиционирование.")
    bullet_list(s, M, 208, 480, [
        ("Три типа", "Личный бренд, компания или сообщество — у каждого свои вопросы."),
        ("Анкета на 12 шагов", "2–4 поля на шаг, ничего лишнего."),
        ("Автозаполнение", "Дайте ссылку на Telegram-канал — ИИ прочитает посты и заполнит анкету."),
        ("Импорт и экспорт", "Загрузка из .json и .docx, бренд-бук — в .docx."),
    ], icon="persona", gap=16, body_lines=2)
    screen(s, "generate", 588, 208, 640)

    # 6. Как это работает
    s = content_slide(prs, 6, "Четыре шага до первого поста")
    steps = [
        ("Зарегистрируйтесь", "Аккаунт создаётся за минуту — нужны только имя, почта и пароль."),
        ("Заполните медиа-образ", "Расскажите о бизнесе или дайте ссылку на канал — ИИ заполнит анкету."),
        ("Сгенерируйте пост", "Выберите платформу и стиль, доработайте текст командами в чате."),
        ("Опубликуйте", "Отправьте пост в свой Telegram-канал одной кнопкой."),
    ]
    cw = (W - 2 * M - 3 * 16) / 4
    rect(s, M + 60, 239, W - 2 * M - 120, 2, fill=T["hairline"])   # линия связи шагов
    for i, (t, b) in enumerate(steps):
        x = M + i * (cw + 16)
        n = rect(s, x + 24, 216, 48, 48, fill=T["brand"], shape=MSO_SHAPE.OVAL)
        text(s, x + 24, 216, 48, 48, str(i + 1), size=20, font=F_BOLD, bold=True, color=T["white"],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        card(s, x, 288, cw, 232)
        text(s, x + 24, 312, cw - 48, 60, t, size=22, font=F_SEMI, line=28)
        text(s, x + 24, 380, cw - 48, 160, b, size=17, color=T["ink2"], line=25)

    # 7. Больше, чем генерация
    s = content_slide(prs, 7, "Больше, чем генерация постов")
    screen(s, "post", M, 184, 640)
    items = [
        ("chat", "Чат правок", "«Сократи вдвое», «Сделай официальнее» — за секунды."),
        ("refresh", "История версий", "Любую прошлую версию можно вернуть."),
        ("link", "Несколько каналов", "Подключайте каналы и чаты Telegram."),
        ("image", "Библиотека картинок", "Все сгенерированные и загруженные фото."),
        ("chart", "Статистика", "Посты, картинки и публикации за всё время."),
        ("download", "Бренд-бук в .docx", "Медиа-образ — готовым документом."),
    ]
    y = 184
    for ic, t, b in items:
        icon_tile(s, 752, y + 2, ic, size=44)
        text(s, 812, y - 2, 404, 56, [[(t, {"font": F_SEMI})], [(b, {"color": T["ink2"], "size": 15})]],
             size=19, line=24)
        y += 72

    # 8. Для кого
    s = content_slide(prs, 8, "Кому подойдёт сервис")
    aud = [
        ("building", "Малому бизнесу", "Кафе, салоны, сервисы и магазины — регулярные посты без SMM-отдела."),
        ("user", "Экспертам и личным брендам", "Юристы, врачи, тренеры пишут о своём деле своим голосом."),
        ("users", "Сообществам и НКО", "Волонтёрские центры, музеи, школы — анонсы и отчёты."),
        ("megaphone", "SMM-специалистам", "Несколько медиа-образов и каналов в одном кабинете."),
        ("news", "Руководителям организаций", "Новости организации без отдельного пресс-секретаря."),
    ]
    cw, ch = (W - 2 * M - 16) / 2, 96
    for i, (ic, t, b) in enumerate(aud):
        col, row = i % 2, i // 2
        x, y = M + col * (cw + 16), 184 + row * (ch + 16)
        card(s, x, y, cw, ch)
        icon_tile(s, x + 24, y + 26, ic)
        text(s, x + 88, y + 20, cw - 112, 60, [[(t, {"font": F_SEMI, "size": 21})], [(b, {"color": T["ink2"]})]],
             size=16, line=24)
    # Пятая карточка — с примером, чтобы сетка 2×3 была полной
    x, y = M + cw + 16, 184 + 2 * (ch + 16)
    c = card(s, x, y, cw, ch, fill=T["brand_tint"])
    c.line.fill.background()
    text(s, x + 24, y + 20, cw - 48, 60, [[("И всем, кому есть что рассказать", {"font": F_SEMI, "color": T["brand"], "size": 21})],
                                          [("Анкета подстраивается под тип: личный бренд, компания или сообщество.", {"color": T["ink"]})]],
         size=16, line=24)

    # 9. Преимущества
    s = content_slide(prs, 9, "Почему выбирают ИИ Пресс-секретарь")
    adv = [
        ("clock", "Экономия времени", "Пост и контент-план — за минуты, а не за часы."),
        ("key", "Экономия бюджета", "Не нужны копирайтер и дизайнер в штате."),
        ("persona", "Единый стиль", "Каждый пост звучит голосом вашего медиа-образа."),
        ("calendar", "Регулярность", "Контент-план помогает публиковать системно."),
        ("check", "Всё под контролем", "ИИ пишет черновик, публикуете вы."),
    ]
    y = 184
    for ic, t, b in adv:
        card(s, M, y, 520, 80)
        icon_tile(s, M + 18, y + 18, ic)
        text(s, M + 80, y + 14, 420, 56, [[(t, {"font": F_SEMI, "size": 20})], [(b, {"color": T["ink2"]})]],
             size=16, line=24)
        y += 88
    screen(s, "plan", 620, 184, 596)

    # 10. Призыв
    s = prs.slides.add_slide(blank)
    picture(s, BUILD / "bg-cta.png", 0, 0, W, H)
    picture(s, BRAND / "mark-white.png", (W - 104) / 2, 136, w=104)
    text(s, 120, 260, W - 240, 72, "Начните с медиа-образа", size=64, font=F_BOLD, bold=True, color=T["white"],
         align=PP_ALIGN.CENTER, line=70, tracking=-40)
    text(s, 200, 344, W - 400, 64, "Зарегистрируйтесь, заполните анкету — и первый пост появится в кабинете.",
         size=22, color=T["white"], align=PP_ALIGN.CENTER, line=32)
    pill(s, W / 2 - 236, 432, 228, "Зарегистрироваться", T["white"], T["logo_deep"])
    pill(s, W / 2 + 8, 432, 228, "Войти в кабинет", T["white"], T["white"], alpha=0.18)
    text(s, 0, 520, W, 28, "press.my-dpr.ru", size=20, font=F_SEMI, color=T["white"], align=PP_ALIGN.CENTER)
    picture(s, BRAND / "lockup-white.png", (W - 200) / 2, H - 72, w=200)

    prs.save(OUT)
    print(f"Презентация сохранена: {OUT}")


if __name__ == "__main__":
    build()
