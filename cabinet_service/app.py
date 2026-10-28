from pathlib import Path
import json
import os
import re
import uuid
from concurrent.futures import ThreadPoolExecutor

import bcrypt
from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from ai_core.image_generator import IMAGE_SIZES, IMAGE_TEMPLATES, STYLE_PRESETS, ImageGenerator, detect_ext, get_sizes_for_model
from ai_core.net_safety import public_url_error
from ai_core.neural_network import ContentGenerator
from ai_core.social_analyzer import analyze_posts_with_ai, detect_platform, fetch_telegram_posts
from ai_core.telegram_publisher import (
    check_bot_is_admin,
    publish_post,
    resolve_chat,
)
from ai_core.tenchat_publisher import publish_post as publish_post_tenchat
from cabinet_service.brand_doc_generator import generate_brand_docx
from config import SECRET_KEY
from database import (
    add_post_revision,
    count_user_tasks,
    create_task,
    fail_unfinished_tasks,
    create_web_user,
    delete_brand_survey,
    delete_channel,
    delete_media_by_id,
    delete_plan_item,
    delete_post_by_id,
    delete_post_image,
    delete_user_by_id,
    get_brand_survey_by_id,
    get_brand_surveys_for_user,
    get_channel_by_id,
    get_channels_for_user,
    get_image_provider_settings,
    get_latest_brand_survey_for_user,
    get_media_by_id_for_user,
    get_media_for_user,
    get_plan_for_user,
    get_plan_stats_for_user,
    get_post_by_id_for_user,
    get_post_images,
    get_post_revisions,
    get_posts_for_user,
    get_provider_settings,
    get_stats_for_user,
    get_task,
    get_text_provider_settings,
    get_user_by_email,
    get_user_by_id,
    is_channel_already_added,
    mark_post_published,
    PROVIDER_PRESETS,
    replace_plan_for_user,
    save_brand_survey,
    save_channel,
    save_media,
    save_post_for_user,
    save_post_image,
    save_provider_settings,
    clear_tenchat_credentials,
    get_tenchat_credentials,
    save_tenchat_credentials,
    update_plan_status,
    update_post_content,
    update_task_status,
    update_tenchat_tokens,
    update_user_field_by_id,
)

BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR / "media"
MEDIA_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Личный кабинет")
# На сервере с https задайте SESSION_COOKIE_SECURE=1 в .env — cookie сессии не уйдёт по http
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, same_site="lax",
                   https_only=os.getenv("SESSION_COOKIE_SECURE", "0") == "1",
                   max_age=14 * 24 * 3600)

_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # CSRF: изменяющий запрос браузера должен прийти с нашего же сайта. Браузер всегда шлёт Origin
    # (или хотя бы Referer) у POST-форм и fetch, подделать их со стороннего сайта нельзя.
    if request.method in _UNSAFE_METHODS:
        source = request.headers.get("origin") or request.headers.get("referer")
        if source:
            from urllib.parse import urlparse
            # Origin: null шлют песочницы iframe и file:// — тоже чужой источник
            if source == "null" or urlparse(source).netloc != request.headers.get("host", ""):
                return JSONResponse({"error": "Запрос отклонён: он пришёл с другого сайта."}, status_code=403)
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if request.headers.get("x-forwarded-proto") == "https" or request.url.scheme == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return response
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def plural(n, forms):
    """Склонение по числу: plural(3, ['день', 'дня', 'дней']) -> 'дня'."""
    n = abs(int(n or 0))
    a, b = n % 100, n % 10
    if 10 < a < 20:
        return forms[2]
    if 1 < b < 5:
        return forms[1]
    if b == 1:
        return forms[0]
    return forms[2]


_PATRONYMIC_ENDINGS = ("вич", "вна", "чна", "ична", "инична", "оглы", "кызы")
_SURNAME_ENDINGS = ("ов", "ова", "ев", "ева", "ёв", "ёва", "ин", "ина", "ын", "ына", "ский", "ская", "цкий", "цкая",
                    "ской", "енко", "ук", "юк", "чук", "ых", "их", "ко")
# Частые имена: окончания вроде «-ина» есть и у имён (Ирина), и у фамилий (Котина), поэтому сначала — словарь
_FIRST_NAMES = set("""
александр алексей анатолий андрей антон аркадий арсений артём артем артур богдан борис вадим валентин валерий василий
виктор виталий владимир владислав всеволод вячеслав геннадий георгий герман глеб григорий давид даниил данил денис
дмитрий евгений егор захар иван игнат игорь илья кирилл константин лев леонид максим марк матвей михаил назар никита
николай олег павел пётр петр платон роман ростислав руслан савелий семён семен сергей станислав степан тимофей тимур
фёдор федор филипп эдуард юрий ян ярослав рашид рустам тарас остап богдан мирон
александра алина алиса алла анастасия ангелина анна антонина арина валентина валерия варвара вера вероника виктория
галина дарья диана ева евгения екатерина елена елизавета жанна зарина зинаида злата инна ирина карина кира кристина
ксения лариса лидия лилия любовь людмила маргарита марина мария милана надежда наталья наталия нина оксана олеся ольга
полина раиса регина светлана софия софья стефания таисия тамара татьяна ульяна элина эльвира юлия яна ярослава
саша шура лёша леша дима женя ваня вова володя коля костя миша паша петя серёжа сережа слава толя юра
аня валя варя галя даша катя ксюша лена лиза люба люда маша надя наташа оля поля света соня таня юля
""".split())


def first_name(full_name):
    """Имя для обращения из поля «Имя»: «Котова Ирина Сергеевна» → «Ирина», «Анна Тестова» → «Анна».
    В обращении имя стоит в именительном падеже, склонять его не нужно. В поле вписано название
    организации (есть кавычки) — имени нет, обращение без имени."""
    raw = str(full_name or "")
    if any(q in raw for q in "«»\"„“"):
        return ""
    words = [w for w in raw.replace(",", " ").split() if w.replace("-", "").isalpha()]
    if not words:
        return ""
    low = [w.lower() for w in words]

    def cap(w):
        return "-".join(p[:1].upper() + p[1:].lower() for p in w.split("-"))
    # Слово из словаря имён — оно и есть имя
    for i, w in enumerate(low):
        if w in _FIRST_NAMES or w.split("-")[0] in _FIRST_NAMES:
            return cap(words[i])
    # Есть отчество — имя стоит перед ним
    for i, w in enumerate(low):
        if i > 0 and w.endswith(_PATRONYMIC_ENDINGS):
            return cap(words[i - 1])
    # Первое слово похоже на фамилию, второе — нет: «Котова Ирина»
    if len(words) >= 2 and low[0].endswith(_SURNAME_ENDINGS) and not low[1].endswith(_SURNAME_ENDINGS):
        return cap(words[1])
    return cap(words[0])


def greeting_for_hour(hour=None):
    """Приветствие по времени суток: утро 5–11, день 11–17, вечер 17–23, ночь 23–5.
    Без аргумента — по часам сервера; на странице скрипт уточняет по часам пользователя."""
    if hour is None:
        from datetime import datetime
        hour = datetime.now().hour
    if 5 <= hour < 11:
        return "Доброе утро"
    if 11 <= hour < 17:
        return "Добрый день"
    if 17 <= hour < 23:
        return "Добрый вечер"
    return "Доброй ночи"


# SQLite хранит CURRENT_TIMESTAMP в UTC; показываем по Москве (DISPLAY_TZ_OFFSET — смещение в часах)
DISPLAY_TZ_OFFSET = int(os.getenv("DISPLAY_TZ_OFFSET", "3"))


def local_dt(value, fmt="%d.%m.%Y %H:%M"):
    """«2026-10-28 10:49:12» (UTC) → «28.10.2026 13:49». Непонятное значение возвращается как есть."""
    from datetime import datetime, timedelta
    raw = str(value or "")
    try:
        dt = datetime.strptime(raw[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return raw
    return (dt + timedelta(hours=DISPLAY_TZ_OFFSET)).strftime(fmt)


templates.env.filters["local_dt"] = local_dt
templates.env.filters["first_name"] = first_name
templates.env.globals["greeting_for_hour"] = greeting_for_hour

# Компоненты дизайн-системы (иконки, логотип) доступны во всех шаблонах как ui.*
templates.env.globals["plural"] = plural
# Числа с неразрывным пробелом между разрядами: 4096 -> «4 096»
templates.env.filters["num"] = lambda n: "{:,}".format(int(n or 0)).replace(",", " ")
templates.env.globals["ui"] = templates.env.get_template("_ui.html").module

content_gen = ContentGenerator()
image_gen = ImageGenerator()

# Фоновые задачи (генерации через ИИ) — общий пул потоков вместо потока на каждый запрос:
# сколько бы задач ни пришло, одновременно к провайдеру идут не больше TASK_WORKERS.
TASK_WORKERS = int(os.getenv("TASK_WORKERS", "4"))
TASK_ACTIVE_LIMIT = int(os.getenv("TASK_ACTIVE_LIMIT", "2"))     # незавершённых задач на пользователя
TASK_HOURLY_LIMIT = int(os.getenv("TASK_HOURLY_LIMIT", "60"))    # задач на пользователя в час
task_pool = ThreadPoolExecutor(max_workers=TASK_WORKERS, thread_name_prefix="task")
fail_unfinished_tasks()

# Загрузка картинок: только настоящие изображения и не больше 10 МБ
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def is_image(data: bytes) -> bool:
    """PNG, JPEG, WebP или GIF по сигнатуре файла — расширению и MIME из браузера не доверяем."""
    return (data[:8] == b"\x89PNG\r\n\x1a\n" or data[:3] == b"\xff\xd8\xff"
            or (data[:4] == b"RIFF" and data[8:12] == b"WEBP") or data[:4] == b"GIF8")


def to_int(value, default=None):
    """int из поля формы или query; мусор — default, а не 500."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return default


def get_user_content_gen(user: dict) -> ContentGenerator:
    """Возвращает ContentGenerator с настройками text-провайдера пользователя."""
    settings = get_text_provider_settings(user["id"])
    if settings and settings.get("api_key"):
        return ContentGenerator(provider_settings=settings)
    return content_gen


def get_user_image_gen(user: dict) -> ImageGenerator:
    """Возвращает ImageGenerator с настройками image-провайдера пользователя."""
    settings = get_image_provider_settings(user["id"])
    if settings and settings.get("api_key"):
        return ImageGenerator(provider_settings=settings)
    return image_gen

PLATFORMS = [
    ("instagram", "Instagram"),
    ("linkedin", "LinkedIn"),
    ("telegram", "Telegram"),
    ("twitter", "Twitter/X"),
    ("tenchat", "TenChat"),
    ("ad", "Рекламный пост"),
]

PLATFORM_LABELS = dict(PLATFORMS)

def platform_label(platform: str) -> str:
    return PLATFORM_LABELS.get(platform, platform)


class NotAuthenticated(Exception):
    pass


@app.exception_handler(NotAuthenticated)
async def not_authenticated_handler(request: Request, exc: NotAuthenticated):
    return RedirectResponse(url="/login", status_code=303)


def current_user(request: Request) -> dict:
    user_id = request.session.get("user_id")
    if not user_id:
        raise NotAuthenticated()
    user = get_user_by_id(user_id)
    if not user:
        request.session.clear()
        raise NotAuthenticated()
    return user


def flash(request: Request, message: str):
    request.session["flash"] = message


def render(request: Request, template: str, status_code: int = 200, **context):
    context.setdefault("user", None)
    context["flash_message"] = request.session.pop("flash", None)
    # Активный медиа-образ — для карточки внизу боковой навигации
    if context["user"] and "active_persona" not in context:
        context["active_persona"] = get_latest_brand_survey_for_user(context["user"]["id"])
    return templates.TemplateResponse(request, template, context, status_code=status_code)


def business_name_of(user: dict) -> str:
    """Возвращает название вида бизнеса. Оставлено для совместимости (профили без медиа-образа)."""
    from keyboards.reply_keyboards import BUSINESS_TYPES
    return BUSINESS_TYPES.get(str(user.get("business_type")), {}).get("name", "Не указан")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root(request: Request):
    # Посадочная страница с описанием сервиса
    return render(request, "landing.html")


@app.get("/presentation-tz")
def presentation_tz(request: Request):
    # Техническое задание на создание презентации сервиса
    return render(request, "presentation_tz.html")


@app.get("/presentation.{ext}")
def presentation_file(ext: str):
    # Готовая презентация лежит в корне проекта (её собирает deploy/generate_presentation.py)
    if ext not in ("pdf", "pptx"):
        raise HTTPException(status_code=404)
    path = BASE_DIR.parent / f"ИИ_Пресс-секретарь_презентация.{ext}"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Презентация ещё не собрана")
    from fastapi.responses import FileResponse
    return FileResponse(path, filename=path.name)


# === РЕГИСТРАЦИЯ ===

@app.get("/register")
def register_form(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/dashboard", status_code=303)
    return render(request, "register.html")


@app.post("/register")
def register_submit(
    request: Request,
    name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
):
    email = email.strip().lower()
    errors = []
    if len(password) < 8:
        errors.append("Пароль должен быть не короче 8 символов.")
    if len(password.encode("utf-8")) > 72:
        errors.append("Пароль слишком длинный: не больше 72 байт (около 36 русских или 72 латинских символов).")
    if password != password_confirm:
        errors.append("Пароли не совпадают.")
    if "@" not in email or "." not in email.split("@")[-1]:
        errors.append("Введи корректный email.")
    if not errors and get_user_by_email(email):
        errors.append("Пользователь с таким email уже зарегистрирован.")

    if errors:
        return render(
            request, "register.html", status_code=400,
            errors=errors,
            form={"name": name, "phone": phone, "email": email},
        )

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user_id = create_web_user(email, password_hash, name, phone)
    request.session["user_id"] = user_id
    flash(request, "Регистрация завершена. Начните с медиа-образа — посты пишутся на его основе.")
    return RedirectResponse("/survey", status_code=303)


# === ВХОД / ВЫХОД ===

@app.get("/login")
def login_form(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/dashboard", status_code=303)
    return render(request, "login.html")


@app.post("/login")
def login_submit(request: Request, email: str = Form(...), password: str = Form(...)):
    email = email.strip().lower()
    user = get_user_by_email(email)
    valid = (
        user is not None
        and user["password_hash"]
        and len(password.encode("utf-8")) <= 72
        and bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8"))
    )
    if not valid:
        return render(
            request, "login.html", status_code=400,
            errors=["Неверный email или пароль."], form={"email": email},
        )

    request.session["user_id"] = user["id"]
    return RedirectResponse("/dashboard", status_code=303)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# === КАБИНЕТ ===

@app.get("/dashboard")
def dashboard(request: Request, user: dict = Depends(current_user)):
    latest_survey = get_latest_brand_survey_for_user(user["id"])
    recent_posts = get_posts_for_user(user["id"], limit=3)
    for p in recent_posts:
        p["images"] = get_post_images(p["id"], user["id"])
    all_posts = get_posts_for_user(user["id"], limit=10000)
    counters = {
        "posts": len(all_posts),
        "images": len(get_media_for_user(user["id"], limit=10000)),
        "published": sum(1 for p in all_posts if p.get("published")),
        "surveys": len(get_brand_surveys_for_user(user["id"])),
    }
    return render(request, "dashboard.html", user=user, latest_survey=latest_survey,
                  active_persona=latest_survey, recent_posts=recent_posts,
                  counters=counters, platform_label=platform_label)


@app.get("/profile/edit")
def profile_edit_form(request: Request, user: dict = Depends(current_user)):
    provider = get_provider_settings(user["id"])
    return render(request, "profile_edit.html", user=user,
                  provider=provider, provider_presets=PROVIDER_PRESETS)


@app.post("/profile/edit")
def profile_edit_submit(
    request: Request,
    name: str = Form(...),
    phone: str = Form(...),
    user: dict = Depends(current_user),
):
    update_user_field_by_id(user["id"], "name", name)
    update_user_field_by_id(user["id"], "phone", phone)
    flash(request, "Профиль обновлён.")
    return RedirectResponse("/dashboard", status_code=303)


# === НАСТРОЙКИ ПРОВАЙДЕРА ИИ ===

@app.get("/provider")
def provider_form(request: Request, user: dict = Depends(current_user)):
    provider = get_provider_settings(user["id"])
    return render(request, "provider.html", user=user,
                  provider=provider, provider_presets=PROVIDER_PRESETS)


@app.post("/provider")
def provider_submit(
    request: Request,
    # Text provider
    text_provider_type: str = Form(...),
    text_api_key: str = Form(""),
    text_base_url: str = Form(""),
    text_model: str = Form(""),
    text_use_global: str = Form(""),
    # Image provider
    image_provider_type: str = Form(...),
    image_api_key: str = Form(""),
    image_base_url: str = Form(""),
    image_model: str = Form(""),
    image_use_global: str = Form(""),
    user: dict = Depends(current_user),
):
    errors = []

    # Валидация text-провайдера
    if text_provider_type not in PROVIDER_PRESETS:
        errors.append("Выберите провайдера для текста.")
    text_preset = PROVIDER_PRESETS.get(text_provider_type, {})
    if not text_use_global and text_preset.get("needs_key") and not text_api_key.strip():
        errors.append("Укажите API ключ для текстового провайдера или выберите «Использовать глобальные настройки».")
    if not text_use_global and text_provider_type == "custom" and not text_base_url.strip():
        errors.append("Для кастомного текстового провайдера укажите Base URL.")

    # Валидация image-провайдера
    if image_provider_type not in PROVIDER_PRESETS:
        errors.append("Выберите провайдера для изображений.")
    image_preset = PROVIDER_PRESETS.get(image_provider_type, {})
    if not image_use_global and image_preset.get("needs_key") and not image_api_key.strip():
        errors.append("Укажите API ключ для провайдера изображений или выберите «Использовать глобальные настройки».")
    if not image_use_global and image_provider_type == "custom" and not image_base_url.strip():
        errors.append("Для кастомного image-провайдера укажите Base URL.")
    # Свой адрес провайдера — только публичный https: сервер отправляет на него запросы и показывает ответ
    for label, use_global, base in (("текстового", text_use_global, text_base_url), ("image-", image_use_global, image_base_url)):
        if not use_global and base.strip():
            url_error = public_url_error(base)
            if url_error:
                errors.append(f"Base URL {label}провайдера: {url_error}")
    if not image_preset.get("supports_images", True) and not image_use_global:
        errors.append(f"Провайдер «{image_preset.get('name')}» не поддерживает генерацию изображений. Выберите другой.")

    if errors:
        return render(
            request, "provider.html", status_code=400,
            user=user, provider_presets=PROVIDER_PRESETS, errors=errors,
            form={
                "text_provider_type": text_provider_type, "text_api_key": text_api_key,
                "text_base_url": text_base_url, "text_model": text_model,
                "image_provider_type": image_provider_type, "image_api_key": image_api_key,
                "image_base_url": image_base_url, "image_model": image_model,
            },
        )

    # Если "использовать глобальные" — сохраняем пустой ключ (будет использован глобальный)
    final_text_key = "" if text_use_global else text_api_key.strip()
    final_image_key = "" if image_use_global else image_api_key.strip()

    # Подставляем дефолтные значения из пресетов
    final_text_base = text_base_url.strip() or text_preset.get("base_url", "")
    final_text_model = text_model.strip() or text_preset.get("text_model", "")
    final_image_base = image_base_url.strip() or image_preset.get("base_url", "")
    final_image_model = image_model.strip() or image_preset.get("image_model", "")

    save_provider_settings(
        user["id"],
        text_provider_type, final_text_key, final_text_base, final_text_model,
        image_provider_type, final_image_key, final_image_base, final_image_model,
    )
    flash(request, "Провайдеры ИИ настроены: текст — «%s», изображения — «%s»." % (
        text_preset.get("name", text_provider_type),
        image_preset.get("name", image_provider_type),
    ))
    return RedirectResponse("/provider", status_code=303)


@app.get("/tenchat")
def tenchat_form(request: Request, user: dict = Depends(current_user)):
    creds = get_tenchat_credentials(user["id"])
    return render(request, "tenchat.html", user=user, creds=creds)


@app.post("/tenchat")
def tenchat_submit(
    request: Request,
    tenchat_username: str = Form(...),
    tenchat_tcrf: str = Form(...),
    user: dict = Depends(current_user),
):
    errors = []
    username = tenchat_username.strip().lstrip("@")
    tcrf = tenchat_tcrf.strip()

    if not username:
        errors.append("Укажите username в TenChat.")
    if not tcrf:
        errors.append("Укажите ключ TCRF (refresh token).")

    if errors:
        return render(
            request, "tenchat.html", status_code=400,
            user=user, creds=get_tenchat_credentials(user["id"]),
            errors=errors,
            form={"tenchat_username": username, "tenchat_tcrf": tcrf},
        )

    save_tenchat_credentials(user["id"], username, tcrf)
    flash(request, "TenChat подключён: @%s. Refresh token сохранён." % username)
    return RedirectResponse("/tenchat", status_code=303)


@app.post("/tenchat/disconnect")
def tenchat_disconnect(request: Request, user: dict = Depends(current_user)):
    clear_tenchat_credentials(user["id"])
    flash(request, "TenChat отключён. Ключи сессии удалены.")
    return RedirectResponse("/tenchat", status_code=303)


@app.get("/generate")
def generate_form(request: Request, user: dict = Depends(current_user),
                  plan_id: str = Query(""), platform: str = Query(""),
                  idea: str = Query("")):
    latest_survey = get_latest_brand_survey_for_user(user["id"])
    surveys = get_brand_surveys_for_user(user["id"])
    prefill = None
    if plan_id:
        prefill = {"plan_id": plan_id, "platform": platform, "idea": idea}
    return render(request, "generate.html", user=user, platforms=PLATFORMS,
                  latest_survey=latest_survey, surveys=surveys, prefill=prefill)


@app.post("/generate")
def generate_submit(
    request: Request,
    platform: str = Form(...),
    style: str = Form(...),
    wishes: str = Form(""),
    survey_id: str = Form(""),
    user: dict = Depends(current_user),
):
    # Выбираем опрос медиа-образа: явно указанный или последний
    brand_data = None
    if survey_id:
        try:
            sid = int(survey_id)
        except ValueError:
            sid = None
        if sid:
            survey = get_brand_survey_by_id(sid, user["id"])
            if survey:
                brand_data = survey["data"]
    if not brand_data:
        latest = get_latest_brand_survey_for_user(user["id"])
        if latest:
            brand_data = latest["data"]

    if not brand_data:
        # Нет медиа-образа — возвращаем форму с подсказкой
        surveys = get_brand_surveys_for_user(user["id"])
        return render(
            request, "generate.html", status_code=400,
            user=user, platforms=PLATFORMS, surveys=surveys,
            latest_survey=None,
            errors=["Сначала создайте медиа-образ — посты генерируются на его основе."],
        )

    user_gen = get_user_content_gen(user)
    try:
        content = user_gen.generate_post_from_brand_profile(brand_data, platform, style, wishes)
    except Exception as e:
        surveys = get_brand_surveys_for_user(user["id"])
        latest_survey = get_latest_brand_survey_for_user(user["id"])
        return render(
            request, "generate.html", status_code=502,
            user=user, platforms=PLATFORMS, surveys=surveys,
            latest_survey=latest_survey,
            errors=[f"Ошибка генерации: {e}. Проверьте настройки провайдера в разделе «ИИ»."],
            form={"platform": platform, "style": style, "wishes": wishes},
        )
    save_post_for_user(user["id"], platform, content, style, wishes)
    latest_survey = get_latest_brand_survey_for_user(user["id"])
    return render(
        request, "generate.html", user=user, platforms=PLATFORMS, result=content,
        latest_survey=latest_survey,
        form={"platform": platform, "style": style, "wishes": wishes},
    )

@app.get("/history")
def history(request: Request, user: dict = Depends(current_user)):
    posts = get_posts_for_user(user["id"], limit=50)
    # Добавляем изображения к каждому посту
    for p in posts:
        p["images"] = get_post_images(p["id"], user["id"])
    return render(request, "history.html", user=user, posts=posts, platform_label=platform_label)


@app.get("/posts/{post_id}")
def post_detail(request: Request, post_id: int, user: dict = Depends(current_user)):
    post = get_post_by_id_for_user(post_id, user["id"])
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    images = get_post_images(post_id, user["id"])
    revisions = get_post_revisions(post_id, user["id"])
    return render(request, "post_detail.html", user=user, post=post,
                  images=images, revisions=revisions,
                  platform_label=platform_label, templates=IMAGE_TEMPLATES)


@app.get("/posts/{post_id}/edit")
def post_edit_form(request: Request, post_id: int, user: dict = Depends(current_user)):
    post = get_post_by_id_for_user(post_id, user["id"])
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    return render(request, "post_edit.html", user=user, post=post, platform_label=platform_label)


@app.post("/posts/{post_id}/edit")
def post_edit_submit(
    request: Request,
    post_id: int,
    content: str = Form(...),
    user: dict = Depends(current_user),
):
    post = get_post_by_id_for_user(post_id, user["id"])
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    content = content.strip()
    if not content:
        return render(
            request, "post_edit.html", status_code=400,
            user=user, post=post, platform_label=platform_label,
            errors=["Текст поста не может быть пустым."],
        )
    update_post_content(user["id"], post_id, content)
    add_post_revision(post_id, user["id"], content)
    flash(request, "Пост обновлён.")
    return RedirectResponse(f"/posts/{post_id}", status_code=303)


@app.post("/api/posts/{post_id}/edit-text")
def api_post_edit_text(
    post_id: int,
    content: str = Form(...),
    user: dict = Depends(current_user),
):
    """AJAX-сохранение текста поста (inline-редактор). Сохраняет ревизию."""
    post = get_post_by_id_for_user(post_id, user["id"])
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    content = content.strip()
    if not content:
        return JSONResponse({"error": "Текст не может быть пустым"}, status_code=400)

    update_post_content(user["id"], post_id, content)
    add_post_revision(post_id, user["id"], content)

    return JSONResponse({"ok": True, "content": content})


@app.post("/posts/{post_id}/delete")
def post_delete(request: Request, post_id: int, user: dict = Depends(current_user)):
    post = get_post_by_id_for_user(post_id, user["id"])
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    # Удаляем изображения поста
    images = get_post_images(post_id, user["id"])
    for img in images:
        fp = MEDIA_DIR / img["filename"]
        if fp.exists():
            fp.unlink()
    delete_post_by_id(user["id"], post_id)
    flash(request, "Пост удалён.")
    return RedirectResponse("/history", status_code=303)


# === ИЗОБРАЖЕНИЯ ПОСТА ===

@app.post("/posts/{post_id}/images/upload")
async def post_image_upload(request: Request, post_id: int, user: dict = Depends(current_user)):
    post = get_post_by_id_for_user(post_id, user["id"])
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")

    form = await request.form()
    files = form.getlist("files")
    if not files:
        flash(request, "Выберите файлы для загрузки.")
        return RedirectResponse(f"/posts/{post_id}", status_code=303)

    uploaded = skipped = 0
    for upload in files:
        if not upload or not upload.filename:
            continue
        raw = await upload.read(MAX_IMAGE_BYTES + 1)
        if not raw or len(raw) > MAX_IMAGE_BYTES or not is_image(raw):
            skipped += 1
            continue
        ext = detect_ext(raw)
        filename = f"{uuid.uuid4().hex}{ext}"
        (MEDIA_DIR / filename).write_bytes(raw)
        save_post_image(post_id, user["id"], filename, source="upload")
        uploaded += 1

    note = f" Пропущено файлов: {skipped} — нужны JPG, PNG, WebP или GIF до 10 МБ." if skipped else ""
    if uploaded:
        flash(request, f"Загружено изображений: {uploaded}.{note}")
    else:
        flash(request, "Не удалось загрузить изображения." + note)
    return RedirectResponse(f"/posts/{post_id}", status_code=303)


@app.post("/posts/{post_id}/images/generate")
def post_image_generate(request: Request, post_id: int, user: dict = Depends(current_user)):
    post = get_post_by_id_for_user(post_id, user["id"])
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")

    # Генерируем промпт из текста поста
    user_img_gen = get_user_image_gen(user)
    # Берём первые 500 символов поста как основу для промпта
    post_text = (post["content"] or "")[:500]
    prompt = f"Create a professional social media image for this post. Post text: {post_text}. Style: modern, clean, eye-catching."

    try:
        image_bytes = user_img_gen.generate(prompt, "square")
    except Exception as e:
        flash(request, f"Ошибка генерации изображения: {e}")
        return RedirectResponse(f"/posts/{post_id}", status_code=303)

    ext = detect_ext(image_bytes)
    filename = f"{uuid.uuid4().hex}{ext}"
    (MEDIA_DIR / filename).write_bytes(image_bytes)
    save_post_image(post_id, user["id"], filename, source="generated")
    flash(request, "Изображение сгенерировано.")
    return RedirectResponse(f"/posts/{post_id}", status_code=303)


@app.post("/posts/{post_id}/images/{image_id}/delete")
def post_image_delete(request: Request, post_id: int, image_id: int, user: dict = Depends(current_user)):
    post = get_post_by_id_for_user(post_id, user["id"])
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    filename = delete_post_image(image_id, user["id"])
    if filename:
        fp = MEDIA_DIR / filename
        if fp.exists():
            fp.unlink()
        flash(request, "Изображение удалено.")
    return RedirectResponse(f"/posts/{post_id}", status_code=303)


@app.get("/plan")
def plan_form(request: Request, user: dict = Depends(current_user)):
    items = get_plan_for_user(user["id"])
    status_counts = get_plan_stats_for_user(user["id"])
    return render(
        request, "plan.html",
        user=user, plan=items, status_counts=status_counts, platform_label=platform_label,
    )


@app.post("/plan")
def plan_submit(request: Request, days: str = Form("7"), user: dict = Depends(current_user)):
    days = max(1, min(to_int(days, 7), 14))
    user_gen = get_user_content_gen(user)
    latest = get_latest_brand_survey_for_user(user["id"])
    if latest:
        plan = user_gen.generate_content_plan_from_brand_profile(latest["data"], days)
    else:
        # Fallback — простой шаблонный план без медиа-образа
        plan = user_gen.generate_content_plan("бизнес", "не указано", days)
    replace_plan_for_user(user["id"], plan)
    flash(request, f"Контент-план на {days} дн. сохранён.")
    return RedirectResponse("/plan", status_code=303)


@app.post("/plan/{item_id}/status")
def plan_status_submit(
    request: Request,
    item_id: int,
    status: str = Form(...),
    user: dict = Depends(current_user),
):
    try:
        found = update_plan_status(user["id"], item_id, status)
        flash(request, "Статус пункта обновлён." if found else "Пункт плана не найден.")
    except ValueError:
        flash(request, "Недопустимый статус.")
    return RedirectResponse("/plan", status_code=303)


@app.post("/plan/{item_id}/delete")
def plan_item_delete(request: Request, item_id: int, user: dict = Depends(current_user)):
    found = delete_plan_item(user["id"], item_id)
    flash(request, "Пункт плана удалён." if found else "Пункт плана не найден.")
    return RedirectResponse("/plan", status_code=303)


@app.get("/stats")
def stats(request: Request, user: dict = Depends(current_user)):
    return render(request, "stats.html", user=user, stats=get_stats_for_user(user["id"]))


@app.get("/delete-account")
def delete_confirm_form(request: Request, user: dict = Depends(current_user)):
    return render(request, "delete_confirm.html", user=user)


@app.post("/delete-account")
def delete_account_submit(
    request: Request, confirm: str = Form(""), user: dict = Depends(current_user)
):
    if confirm != "yes":
        return RedirectResponse("/dashboard", status_code=303)
    for filename in delete_user_by_id(user["id"]):
        fp = MEDIA_DIR / filename
        if fp.exists():
            fp.unlink()
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# === ГЕНЕРАЦИЯ КАРТИНОК ===

@app.get("/images")
def images_gallery(request: Request, user: dict = Depends(current_user)):
    items = get_media_for_user(user["id"])
    return render(request, "images.html", user=user, images=items)


@app.get("/images/generate")
def image_generate_form(request: Request, user: dict = Depends(current_user)):
    # Размеры зависят от модели image-провайдера
    img_settings = get_image_provider_settings(user["id"])
    if img_settings and img_settings.get("image_model"):
        sizes = get_sizes_for_model(img_settings["image_model"])
    else:
        sizes = IMAGE_SIZES
    return render(
        request, "image_generate.html",
        user=user, sizes=sizes, styles=STYLE_PRESETS, templates=IMAGE_TEMPLATES,
    )


@app.post("/images/generate")
def image_generate_submit(
    request: Request,
    prompt: str = Form(...),
    size: str = Form("square"),
    style: str = Form("none"),
    user: dict = Depends(current_user),
):
    # Размеры зависят от модели
    img_settings = get_image_provider_settings(user["id"])
    if img_settings and img_settings.get("image_model"):
        sizes = get_sizes_for_model(img_settings["image_model"])
    else:
        sizes = IMAGE_SIZES

    prompt = prompt.strip()
    if not prompt:
        return render(
            request, "image_generate.html", status_code=400,
            user=user, sizes=sizes, styles=STYLE_PRESETS, templates=IMAGE_TEMPLATES,
            form={"prompt": prompt, "size": size, "style": style},
            errors=["Опишите, что нужно нарисовать."],
        )

    user_img_gen = get_user_image_gen(user)
    full_prompt = user_img_gen.build_prompt(prompt, style)
    try:
        image_bytes = user_img_gen.generate(full_prompt, size)
    except Exception as e:
        return render(
            request, "image_generate.html", status_code=502,
            user=user, sizes=sizes, styles=STYLE_PRESETS, templates=IMAGE_TEMPLATES,
            form={"prompt": prompt, "size": size, "style": style},
            errors=[f"Ошибка генерации картинки: {e}"],
        )

    filename = f"{uuid.uuid4().hex}{detect_ext(image_bytes)}"
    (MEDIA_DIR / filename).write_bytes(image_bytes)
    save_media(user["id"], prompt, style, filename)
    flash(request, "Картинка сгенерирована и сохранена в библиотеку.")
    return RedirectResponse("/images", status_code=303)


@app.post("/images/{media_id}/delete")
def image_delete(request: Request, media_id: int, user: dict = Depends(current_user)):
    item = get_media_by_id_for_user(media_id, user["id"])
    if not item:
        raise HTTPException(status_code=404, detail="Картинка не найдена")
    filename = delete_media_by_id(user["id"], media_id)
    if filename:
        file_path = MEDIA_DIR / filename
        if file_path.exists():
            file_path.unlink()
    flash(request, "Картинка удалена.")
    return RedirectResponse("/images", status_code=303)


# === ОПРОСЫ МЕДИА-ОБРАЗА ===

@app.get("/surveys")
def survey_list(request: Request, user: dict = Depends(current_user)):
    surveys = get_brand_surveys_for_user(user["id"])
    return render(request, "survey_list.html", user=user, surveys=surveys)


@app.get("/survey")
def survey_form(request: Request, user: dict = Depends(current_user)):
    return render(request, "survey.html", user=user)


@app.get("/survey/import")
def survey_import_form(request: Request, user: dict = Depends(current_user)):
    return render(request, "survey_import.html", user=user)


@app.post("/survey/import")
async def survey_import_submit(request: Request, user: dict = Depends(current_user)):
    import json as _json
    from docx import Document as _DocxDocument
    from io import BytesIO as _BytesIO

    form = await request.form()
    upload = form.get("file")
    if not upload or not upload.filename:
        return render(
            request, "survey_import.html", status_code=400,
            user=user, errors=["Выберите файл для загрузки."],
        )

    filename = upload.filename.lower()
    raw = await upload.read()

    # --- JSON: прямой импорт ---
    if filename.endswith(".json"):
        try:
            data = _json.loads(raw.decode("utf-8"))
        except Exception as e:
            return render(
                request, "survey_import.html", status_code=400,
                user=user, errors=[f"Ошибка чтения JSON: {e}"],
            )
        # Поддерживаем два формата: {"data": {...}, "title": "..."} или просто {...}
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
            title = str(data.get("title") or "Импортированный образ").strip()[:200]
            survey_data = data["data"]
        elif isinstance(data, dict):
            title = str(data.get("client_name") or data.get("title") or "Импортированный образ").strip()[:200]
            survey_data = data
        else:
            return render(
                request, "survey_import.html", status_code=400,
                user=user, errors=["JSON должен быть объектом с полями опроса."],
            )
        # Гарантируем структуры
        survey_data.setdefault("channels", [])
        survey_data.setdefault("funnel", [])
        survey_id = save_brand_survey(user["id"], title, survey_data)
        flash(request, f"Медиа-образ «{title}» импортирован из JSON.")
        return RedirectResponse(f"/surveys/{survey_id}", status_code=303)

    # --- DOCX: разбор через PiAPI ---
    if filename.endswith(".docx"):
        try:
            doc = _DocxDocument(_BytesIO(raw))
        except Exception as e:
            return render(
                request, "survey_import.html", status_code=400,
                user=user, errors=[f"Ошибка чтения .docx: {e}"],
            )

        # Извлекаем весь текст
        lines = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                lines.append(text)
        # Текст из таблиц
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells]
                lines.append(" | ".join(cells))
        doc_text = "\n".join(lines)

        if not doc_text.strip():
            return render(
                request, "survey_import.html", status_code=400,
                user=user, errors=["Документ пустой — нет текста для разбора."],
            )

        # Разбор через PiAPI
        survey_data = content_gen.parse_brand_doc_to_survey(doc_text)
        if not survey_data:
            return render(
                request, "survey_import.html", status_code=502,
                user=user,
                errors=["Не удалось разобрать документ. Проверьте, что PiAPI ключ настроен, и попробуйте снова."],
            )

        title = str(survey_data.get("client_name") or "Импортированный образ").strip()[:200]
        survey_id = save_brand_survey(user["id"], title, survey_data)
        flash(request, f"Медиа-образ «{title}» импортирован из .docx.")
        return RedirectResponse(f"/surveys/{survey_id}", status_code=303)

    return render(
        request, "survey_import.html", status_code=400,
        user=user, errors=["Поддерживаются только файлы .docx и .json"],
    )


@app.post("/survey/submit")
async def survey_submit(request: Request, user: dict = Depends(current_user)):
    try:
        body = await request.json()
    except ValueError:
        body = None
    if not isinstance(body, dict) or not isinstance(body.get("data") or {}, dict):
        return JSONResponse({"ok": False, "error": "Некорректные данные анкеты."}, status_code=400)
    title = str(body.get("title") or "Без названия").strip()[:200] or "Без названия"
    data = body.get("data") or {}
    survey_id = save_brand_survey(user["id"], title, data)
    return {"id": survey_id, "ok": True}


@app.get("/surveys/{survey_id}")
def survey_view(request: Request, survey_id: int, user: dict = Depends(current_user)):
    survey = get_brand_survey_by_id(survey_id, user["id"])
    if not survey:
        raise HTTPException(status_code=404, detail="Опрос не найден")
    return render(request, "survey_view.html", user=user, survey=survey)


@app.get("/surveys/{survey_id}/export")
def survey_export(request: Request, survey_id: int, user: dict = Depends(current_user)):
    survey = get_brand_survey_by_id(survey_id, user["id"])
    if not survey:
        raise HTTPException(status_code=404, detail="Опрос не найден")
    docx_bytes = generate_brand_docx(survey["data"])
    # ASCII-имя для Content-Disposition (latin-1), кириллица не допускается в заголовках
    safe_title = "".join(c if c.isascii() and c.isalnum() else "_" for c in survey["title"])[:80]
    if not safe_title or safe_title == "_" * len(safe_title):
        safe_title = "brand"
    filename = f"Strategiya_brenda_{safe_title}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/surveys/{survey_id}/delete")
def survey_delete(request: Request, survey_id: int, user: dict = Depends(current_user)):
    survey = get_brand_survey_by_id(survey_id, user["id"])
    if not survey:
        raise HTTPException(status_code=404, detail="Опрос не найден")
    delete_brand_survey(user["id"], survey_id)
    flash(request, "Опрос удалён.")
    return RedirectResponse("/surveys", status_code=303)


# === КАНАЛЫ ДЛЯ ПУБЛИКАЦИИ ===

@app.get("/channels")
def channels_list(request: Request, user: dict = Depends(current_user)):
    channels = get_channels_for_user(user["id"])
    return render(request, "channels.html", user=user, channels=channels)


@app.get("/channels/add")
def channel_add_form(request: Request, user: dict = Depends(current_user)):
    return render(request, "channel_add.html", user=user)


@app.post("/channels/add")
def channel_add_submit(
    request: Request,
    chat_input: str = Form(...),
    user: dict = Depends(current_user),
):
    chat_input = chat_input.strip()
    if not chat_input:
        return render(
            request, "channel_add.html", status_code=400,
            user=user, errors=["Введите @username или ID канала/чата."],
            form={"chat_input": chat_input},
        )

    # 1. Разрешаем чат через Telegram API
    info = resolve_chat(chat_input)
    if "error" in info:
        return render(
            request, "channel_add.html", status_code=400,
            user=user, errors=[f"Не удалось найти чат: {info['error']}"],
            form={"chat_input": chat_input},
        )

    chat_id = info["chat_id"]
    title = info["title"]
    username = info["username"]
    chat_type = info["type"]

    # 2. Проверяем, что бот — админ
    is_admin, admin_error = check_bot_is_admin(chat_id)
    if not is_admin:
        return render(
            request, "channel_add.html", status_code=400,
            user=user, errors=[admin_error or "Бот не админ в этом чате."],
            form={"chat_input": chat_input},
        )

    # 3. Проверяем, не добавлен ли уже
    if is_channel_already_added(user["id"], chat_id):
        return render(
            request, "channel_add.html", status_code=400,
            user=user, errors=[f"Канал «{title}» уже добавлен."],
            form={"chat_input": chat_input},
        )

    # 4. Бот общий, поэтому «бот — админ» не доказывает, что канал ваш.
    # Владелец подтверждает канал кодом в его описании: менять описание могут только админы канала.
    pending = {"chat_id": chat_id, "title": title, "username": username, "type": chat_type,
               "code": "press-" + uuid.uuid4().hex[:8]}
    request.session["channel_verify"] = pending
    return render(request, "channel_add.html", user=user, verify=pending)


@app.post("/channels/verify")
def channel_verify_submit(request: Request, user: dict = Depends(current_user)):
    pending = request.session.get("channel_verify")
    if not pending:
        flash(request, "Проверка устарела. Добавьте канал ещё раз.")
        return RedirectResponse("/channels/add", status_code=303)

    info = resolve_chat(str(pending["chat_id"]))
    if "error" in info:
        return render(request, "channel_add.html", status_code=400, user=user, verify=pending,
                      errors=[f"Не удалось проверить канал: {info['error']}"])
    if pending["code"] not in (info.get("description") or ""):
        return render(request, "channel_add.html", status_code=400, user=user, verify=pending,
                      errors=["Код не найден в описании канала. Сохраните описание в Telegram и проверьте ещё раз."])
    is_admin, admin_error = check_bot_is_admin(pending["chat_id"])
    if not is_admin:
        return render(request, "channel_add.html", status_code=400, user=user, verify=pending,
                      errors=[admin_error or "Бот не админ в этом чате."])

    request.session.pop("channel_verify", None)
    if not is_channel_already_added(user["id"], pending["chat_id"]):
        save_channel(user["id"], pending["chat_id"], info["title"], info["username"], info["type"])
    flash(request, f"Канал «{info['title']}» подключён. Код из описания можно удалить.")
    return RedirectResponse("/channels", status_code=303)


@app.post("/channels/{channel_id}/delete")
def channel_delete(request: Request, channel_id: int, user: dict = Depends(current_user)):
    channel = get_channel_by_id(channel_id, user["id"])
    if not channel:
        raise HTTPException(status_code=404, detail="Канал не найден")
    delete_channel(user["id"], channel_id)
    flash(request, f"Канал «{channel['title']}» удалён.")
    return RedirectResponse("/channels", status_code=303)


# === ПУБЛИКАЦИЯ ПОСТА ===

@app.get("/posts/{post_id}/publish")
def publish_form(request: Request, post_id: int, user: dict = Depends(current_user)):
    post = get_post_by_id_for_user(post_id, user["id"])
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    channels = get_channels_for_user(user["id"])
    tenchat = get_tenchat_credentials(user["id"])
    return render(request, "publish.html", user=user, post=post, channels=channels,
                  platform_label=platform_label,
                  tenchat_connected=bool(tenchat),
                  tenchat_username=tenchat["tenchat_username"] if tenchat else None)


@app.post("/posts/{post_id}/publish")
def publish_submit(
    request: Request,
    post_id: int,
    channel_id: str = Form(...),
    user: dict = Depends(current_user),
):
    post = get_post_by_id_for_user(post_id, user["id"])
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")

    try:
        cid = int(channel_id)
    except ValueError:
        cid = None
    if not cid:
        channels = get_channels_for_user(user["id"])
        return render(
            request, "publish.html", status_code=400,
            user=user, post=post, channels=channels, platform_label=platform_label,
            errors=["Выберите канал для публикации."],
        )

    channel = get_channel_by_id(cid, user["id"])
    if not channel:
        raise HTTPException(status_code=404, detail="Канал не найден")

    # Берём первую картинку поста (если есть) для публикации в Telegram
    image_bytes = None
    images = get_post_images(post_id, user["id"])
    if images:
        fp = MEDIA_DIR / images[0]["filename"]
        if fp.exists():
            image_bytes = fp.read_bytes()

    ok, message = publish_post(channel["chat_id"], post["content"], image_bytes=image_bytes)
    if ok:
        mark_post_published(post_id, user["id"], channel["title"])
        flash(request, f"✅ Пост опубликован в «{channel['title']}»")
    else:
        flash(request, f"❌ Ошибка публикации: {message}")

    return RedirectResponse(f"/posts/{post_id}", status_code=303)


@app.post("/posts/{post_id}/publish/tenchat")
def publish_tenchat_submit(request: Request, post_id: int, user: dict = Depends(current_user)):
    post = get_post_by_id_for_user(post_id, user["id"])
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")

    creds = get_tenchat_credentials(user["id"])
    if not creds:
        flash(request, "❌ TenChat не подключён. Настройте ключи сессии на странице /tenchat.")
        return RedirectResponse(f"/posts/{post_id}/publish", status_code=303)

    ok, result, new_tcrf = publish_post_tenchat(
        creds["tenchat_tcrf"],
        post["content"],
    )

    # Обновляем TCRF (одноразовый — после каждого refresh он меняется)
    if new_tcrf:
        update_tenchat_tokens(user["id"], new_tcrf)

    if ok:
        mark_post_published(post_id, user["id"], "TenChat")
        url = result.get("url") if isinstance(result, dict) else None
        flash(request, f"✅ Пост опубликован в TenChat" + (f": {url}" if url else ""))
    else:
        flash(request, f"❌ Ошибка публикации в TenChat: {result}")

    return RedirectResponse(f"/posts/{post_id}", status_code=303)


# === ФОНОВАЯ ГЕНЕРАЦИЯ (AJAX) ===

def _run_post_generation(task_id, user_id, platform, style, wishes, survey_id, plan_id=None):
    """Фоновая генерация поста."""
    try:
        update_task_status(task_id, 'running')
        brand_data = None
        if survey_id:
            survey = get_brand_survey_by_id(survey_id, user_id)
            if survey:
                brand_data = survey["data"]
        if not brand_data:
            latest = get_latest_brand_survey_for_user(user_id)
            if latest:
                brand_data = latest["data"]
        if not brand_data:
            update_task_status(task_id, 'error', error="Нет медиа-образа. Создайте медиа-образ и повторите.")
            return
        settings = get_text_provider_settings(user_id)
        gen = ContentGenerator(provider_settings=settings) if settings and settings.get("api_key") else content_gen
        content = gen.generate_post_from_brand_profile(brand_data, platform, style, wishes)
        post_id = save_post_for_user(user_id, platform, content, style, wishes)
        # Пост из плана — пока только черновик: «Опубликовано» пункт получает вручную в плане
        update_task_status(task_id, 'done', result_json=json.dumps({"post_id": post_id, "content": content}))
    except Exception as e:
        update_task_status(task_id, 'error', error=str(e))


def _run_plan_generation(task_id, user_id, days):
    """Фоновая генерация контент-плана."""
    try:
        update_task_status(task_id, 'running')
        settings = get_text_provider_settings(user_id)
        gen = ContentGenerator(provider_settings=settings) if settings and settings.get("api_key") else content_gen
        latest = get_latest_brand_survey_for_user(user_id)
        if latest:
            plan = gen.generate_content_plan_from_brand_profile(latest["data"], days)
        else:
            plan = gen.generate_content_plan("бизнес", "не указано", days)
        replace_plan_for_user(user_id, plan)
        update_task_status(task_id, 'done', result_json=json.dumps({"days": days, "items": len(plan)}))
    except Exception as e:
        update_task_status(task_id, 'error', error=str(e))


def _run_modify_post(task_id, user_id, post_id, instruction):
    """Фоновая модификация поста по инструкции пользователя."""
    try:
        update_task_status(task_id, 'running')

        post = get_post_by_id_for_user(post_id, user_id)
        if not post:
            update_task_status(task_id, 'error', error="Пост не найден")
            return

        if not instruction.strip():
            update_task_status(task_id, 'error', error="Инструкция не может быть пустой")
            return

        # Получаем AI-провайдер
        settings = get_text_provider_settings(user_id)
        gen = ContentGenerator(provider_settings=settings) if settings and settings.get("api_key") else content_gen

        new_content = gen.modify_post(post["content"], instruction.strip())

        # Сохраняем новую версию
        update_post_content(user_id, post_id, new_content)
        add_post_revision(post_id, user_id, new_content)

        update_task_status(task_id, 'done', result_json=json.dumps({
            "content": new_content,
            "instruction": instruction.strip(),
        }, ensure_ascii=False))

    except Exception as e:
        update_task_status(task_id, 'error', error=str(e))


def _run_social_analysis(task_id, user_id, url, manual_posts):
    """Фоновый анализ профиля соцсети."""
    try:
        update_task_status(task_id, 'running')

        platform_info = detect_platform(url)
        posts = []

        # Если пользователь вставил тексты постов вручную
        if manual_posts and manual_posts.strip():
            blocks = re.split(r'\n{2,}', manual_posts.strip())
            for block in blocks:
                block = block.strip()
                if len(block) > 20:
                    posts.append({"text": block, "date": ""})

        # Если URL — Telegram, загружаем посты автоматически
        if not posts and platform_info["platform"] == "telegram" and platform_info["fetchable"]:
            posts = fetch_telegram_posts(platform_info["channel"])

        if not posts:
            update_task_status(task_id, 'error',
                error="Не удалось загрузить посты. Для VK и TenChat вставьте тексты постов вручную (по 2+ постов через пустую строку).")
            return

        # AI-анализ
        settings = get_text_provider_settings(user_id)
        result = analyze_posts_with_ai(posts, provider_settings=settings)

        if "error" in result:
            update_task_status(task_id, 'error', error=result["error"])
            return

        result["platform_info"] = platform_info
        result["posts_count"] = len(posts)
        update_task_status(task_id, 'done', result_json=json.dumps(result, ensure_ascii=False))

    except Exception as e:
        update_task_status(task_id, 'error', error=str(e))


def _run_image_generation(task_id, user_id, prompt, size, style, reference_image_bytes=None):
    """Фоновая генерация картинки."""
    try:
        update_task_status(task_id, 'running')
        settings = get_image_provider_settings(user_id)
        gen = ImageGenerator(provider_settings=settings) if settings and settings.get("api_key") else image_gen
        full_prompt = gen.build_prompt(prompt, style)
        if reference_image_bytes:
            # Для image-to-image нужен chat/completions — используем text-провайдер
            text_settings = get_text_provider_settings(user_id)
            image_bytes = gen.generate_with_reference(full_prompt, reference_image_bytes, size, chat_settings=text_settings)
        else:
            image_bytes = gen.generate(full_prompt, size)
        filename = f"{uuid.uuid4().hex}{detect_ext(image_bytes)}"
        (MEDIA_DIR / filename).write_bytes(image_bytes)
        save_media(user_id, prompt, style, filename)
        update_task_status(task_id, 'done', result_json=json.dumps({"filename": filename}))
    except Exception as e:
        update_task_status(task_id, 'error', error=str(e))


def _run_analyze_post_image(task_id, user_id, post_id):
    """Фоновый анализ поста — предлагает концепции изображений."""
    try:
        update_task_status(task_id, 'running')
        post = get_post_by_id_for_user(post_id, user_id)
        if not post:
            update_task_status(task_id, 'error', error="Пост не найден")
            return
        post_text = (post["content"] or "")[:2000]

        # Получаем медиа-образ для контекста бренда
        brand_data = None
        latest = get_latest_brand_survey_for_user(user_id)
        if latest:
            brand_data = latest["data"]

        settings = get_text_provider_settings(user_id)
        gen = ContentGenerator(provider_settings=settings) if settings and settings.get("api_key") else content_gen
        concepts = gen.suggest_image_concepts(post_text, brand_data)
        update_task_status(task_id, 'done', result_json=json.dumps({"concepts": concepts}))
    except Exception as e:
        update_task_status(task_id, 'error', error=str(e))


def _run_post_image_generation(task_id, user_id, post_id, template_key=None, custom_prompt=None, custom_style=None, custom_size=None):
    """Фоновая генерация картинки к посту."""
    try:
        update_task_status(task_id, 'running')
        post = get_post_by_id_for_user(post_id, user_id)
        if not post:
            update_task_status(task_id, 'error', error="Пост не найден")
            return
        settings = get_image_provider_settings(user_id)
        gen = ImageGenerator(provider_settings=settings) if settings and settings.get("api_key") else image_gen

        post_text = (post["content"] or "")[:500]

        if custom_prompt:
            # Концепт от ИИ — используем его промпт + текст поста
            prompt = f"{custom_prompt}. Post text for context: {post_text}"
            size = custom_size or "wide"
            style = custom_style or "none"
        elif template_key:
            # Ищем шаблон по ключу
            tpl = None
            for t in IMAGE_TEMPLATES:
                if t["key"] == template_key:
                    tpl = t
                    break
            if tpl:
                prompt = tpl["prompt_template"].replace("{post_text}", post_text)
                size = tpl["size"]
                style = tpl["style"]
            else:
                prompt = f"Create a professional social media image for this post. Post text: {post_text}. Style: modern, clean, eye-catching."
                size = "square"
                style = None
        else:
            # Старое поведение — авто-промпт
            prompt = f"Create a professional social media image for this post. Post text: {post_text}. Style: modern, clean, eye-catching."
            size = "square"
            style = None

        if style:
            prompt = gen.build_prompt(prompt, style)

        image_bytes = gen.generate(prompt, size)
        ext = detect_ext(image_bytes)
        filename = f"{uuid.uuid4().hex}{ext}"
        (MEDIA_DIR / filename).write_bytes(image_bytes)
        save_post_image(post_id, user_id, filename, source="generated")
        update_task_status(task_id, 'done', result_json=json.dumps({"filename": filename}))
    except Exception as e:
        update_task_status(task_id, 'error', error=str(e))


TASK_TYPES = {
    "generate_post", "generate_plan", "generate_image", "generate_post_image", "analyze_post_image",
    "generate_post_image_with_concept", "analyze_social_profile", "modify_post",
}
POST_TASKS = {"generate_post_image", "analyze_post_image", "generate_post_image_with_concept", "modify_post"}


def _task_error(message, status_code=400):
    return JSONResponse({"error": message}, status_code=status_code)


@app.post("/api/tasks")
async def api_start_task(request: Request, user: dict = Depends(current_user)):
    """Запускает фоновую задачу. Возвращает task_id."""
    uid = user["id"]
    form = await request.form()
    task_type_val = form.get("task_type", "")
    if task_type_val not in TASK_TYPES:
        return _task_error("Неизвестный тип задачи.")

    # Лимиты: каждая задача — платный запрос к ИИ через общий ключ
    if count_user_tasks(uid, 15, active_only=True) >= TASK_ACTIVE_LIMIT:
        return _task_error("Дождитесь окончания текущих генераций и повторите.", 429)
    if count_user_tasks(uid, 60) >= TASK_HOURLY_LIMIT:
        return _task_error("Достигнут лимит генераций на этот час. Повторите позже.", 429)

    post_id = None
    if task_type_val in POST_TASKS:
        post_id = to_int(form.get("post_id"))
        if not post_id or not get_post_by_id_for_user(post_id, uid):
            return _task_error("Пост не найден.", 404)

    if task_type_val == "generate_post":
        job = (_run_post_generation, form.get("platform", "telegram"), form.get("style", ""),
               form.get("wishes", ""), to_int(form.get("survey_id")), form.get("plan_id", "") or None)

    elif task_type_val == "generate_plan":
        days = max(1, min(to_int(form.get("days"), 7), 14))
        job = (_run_plan_generation, days)

    elif task_type_val == "generate_image":
        ref_file = form.get("reference_image")
        ref_bytes = None
        if ref_file and hasattr(ref_file, "read"):
            ref_bytes = await ref_file.read(MAX_IMAGE_BYTES + 1)
            if len(ref_bytes) < 100:
                ref_bytes = None  # пустой файл — генерируем без образца
            elif len(ref_bytes) > MAX_IMAGE_BYTES or not is_image(ref_bytes):
                return _task_error("Образец должен быть картинкой JPG, PNG, WebP или GIF до 10 МБ.")
        job = (_run_image_generation, form.get("prompt", ""), form.get("size", "square"),
               form.get("style", "none"), ref_bytes)

    elif task_type_val == "generate_post_image":
        job = (_run_post_image_generation, post_id, form.get("template_key", "") or None)

    elif task_type_val == "analyze_post_image":
        job = (_run_analyze_post_image, post_id)

    elif task_type_val == "generate_post_image_with_concept":
        job = (lambda task_id, uid_, pid: _run_post_image_generation(
            task_id, uid_, pid,
            custom_prompt=form.get("concept_prompt", ""),
            custom_style=form.get("concept_style", "none"),
            custom_size=form.get("concept_size", "square"),
        ), post_id)

    elif task_type_val == "analyze_social_profile":
        job = (_run_social_analysis, form.get("url", ""), form.get("manual_posts", ""))

    else:  # modify_post
        job = (_run_modify_post, post_id, form.get("instruction", ""))

    task_id = create_task(uid, task_type_val)
    task_pool.submit(job[0], task_id, uid, *job[1:])
    return {"task_id": task_id, "status": "pending"}


@app.get("/api/tasks/{task_id}")
def api_task_status(task_id: int, user: dict = Depends(current_user)):
    """Возвращает статус задачи."""
    task = get_task(task_id)
    if not task or task["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    result = {
        "task_id": task["id"],
        "status": task["status"],
        "task_type": task["task_type"],
    }
    if task["status"] == "done" and task["result_json"]:
        result["result"] = json.loads(task["result_json"])
    if task["error"]:
        result["error"] = task["error"]
    return result
