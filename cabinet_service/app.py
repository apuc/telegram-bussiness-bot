from pathlib import Path
import os
import uuid

import bcrypt
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from ai_core.image_generator import IMAGE_SIZES, STYLE_PRESETS, ImageGenerator, detect_ext
from ai_core.neural_network import ContentGenerator
from config import SECRET_KEY
from database import (
    create_web_user,
    delete_media_by_id,
    delete_plan_item,
    delete_post_by_id,
    delete_user_by_id,
    get_media_by_id_for_user,
    get_media_for_user,
    get_plan_for_user,
    get_plan_stats_for_user,
    get_post_by_id_for_user,
    get_posts_for_user,
    get_stats_for_user,
    get_user_by_email,
    get_user_by_id,
    replace_plan_for_user,
    save_media,
    save_post_for_user,
    update_plan_status,
    update_post_content,
    update_user_field_by_id,
)
from keyboards.reply_keyboards import BUSINESS_TYPES

BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR / "media"
MEDIA_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Личный кабинет")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

content_gen = ContentGenerator()
image_gen = ImageGenerator()

PLATFORMS = [
    ("instagram", "Instagram"),
    ("linkedin", "LinkedIn"),
    ("telegram", "Telegram"),
    ("twitter", "Twitter/X"),
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
    return templates.TemplateResponse(request, template, context, status_code=status_code)


def business_name_of(user: dict) -> str:
    return BUSINESS_TYPES.get(str(user["business_type"]), {}).get("name", "Не указан")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/dashboard", status_code=303)
    return RedirectResponse("/login", status_code=303)


# === РЕГИСТРАЦИЯ ===

@app.get("/register")
def register_form(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/dashboard", status_code=303)
    return render(request, "register.html", business_types=BUSINESS_TYPES)


@app.post("/register")
def register_submit(
    request: Request,
    name: str = Form(...),
    phone: str = Form(...),
    business_type: str = Form(...),
    description: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
):
    email = email.strip().lower()
    errors = []
    if business_type not in BUSINESS_TYPES:
        errors.append("Выбери вид бизнеса из списка.")
    if len(password) < 8:
        errors.append("Пароль должен быть не короче 8 символов.")
    if password != password_confirm:
        errors.append("Пароли не совпадают.")
    if "@" not in email or "." not in email.split("@")[-1]:
        errors.append("Введи корректный email.")
    if not errors and get_user_by_email(email):
        errors.append("Пользователь с таким email уже зарегистрирован.")

    if errors:
        return render(
            request, "register.html", status_code=400,
            business_types=BUSINESS_TYPES, errors=errors,
            form={
                "name": name, "phone": phone, "business_type": business_type,
                "description": description, "email": email,
            },
        )

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user_id = create_web_user(email, password_hash, name, phone, int(business_type), description)
    request.session["user_id"] = user_id
    flash(request, "Регистрация завершена! Добро пожаловать.")
    return RedirectResponse("/dashboard", status_code=303)


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
    return render(request, "dashboard.html", user=user, business_name=business_name_of(user))


@app.get("/profile/edit")
def profile_edit_form(request: Request, user: dict = Depends(current_user)):
    return render(request, "profile_edit.html", user=user, business_types=BUSINESS_TYPES)


@app.post("/profile/edit")
def profile_edit_submit(
    request: Request,
    name: str = Form(...),
    phone: str = Form(...),
    business_type: str = Form(...),
    description: str = Form(...),
    user: dict = Depends(current_user),
):
    if business_type not in BUSINESS_TYPES:
        return render(
            request, "profile_edit.html", status_code=400,
            user=user, business_types=BUSINESS_TYPES,
            errors=["Выбери вид бизнеса из списка."],
        )

    update_user_field_by_id(user["id"], "name", name)
    update_user_field_by_id(user["id"], "phone", phone)
    update_user_field_by_id(user["id"], "business_type", int(business_type))
    update_user_field_by_id(user["id"], "description", description)
    flash(request, "Профиль обновлён.")
    return RedirectResponse("/dashboard", status_code=303)


@app.get("/generate")
def generate_form(request: Request, user: dict = Depends(current_user)):
    return render(request, "generate.html", user=user, platforms=PLATFORMS)


@app.post("/generate")
def generate_submit(
    request: Request,
    platform: str = Form(...),
    style: str = Form(...),
    wishes: str = Form(""),
    user: dict = Depends(current_user),
):
    description = user["description"] or "не указано"
    content = content_gen.generate_post_with_style(
        business_name_of(user), description, platform, style, wishes
    )
    save_post_for_user(user["id"], platform, content, style, wishes)
    return render(
        request, "generate.html", user=user, platforms=PLATFORMS, result=content,
        form={"platform": platform, "style": style, "wishes": wishes},
    )


@app.get("/history")
def history(request: Request, user: dict = Depends(current_user)):
    posts = get_posts_for_user(user["id"], limit=50)
    return render(request, "history.html", user=user, posts=posts, platform_label=platform_label)


@app.get("/posts/{post_id}")
def post_detail(request: Request, post_id: int, user: dict = Depends(current_user)):
    post = get_post_by_id_for_user(post_id, user["id"])
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    return render(request, "post_detail.html", user=user, post=post, platform_label=platform_label)


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
    flash(request, "Пост обновлён.")
    return RedirectResponse(f"/posts/{post_id}", status_code=303)


@app.post("/posts/{post_id}/delete")
def post_delete(request: Request, post_id: int, user: dict = Depends(current_user)):
    post = get_post_by_id_for_user(post_id, user["id"])
    if not post:
        raise HTTPException(status_code=404, detail="Пост не найден")
    delete_post_by_id(user["id"], post_id)
    flash(request, "Пост удалён.")
    return RedirectResponse("/history", status_code=303)


@app.get("/plan")
def plan_form(request: Request, user: dict = Depends(current_user)):
    items = get_plan_for_user(user["id"])
    status_counts = get_plan_stats_for_user(user["id"])
    return render(
        request, "plan.html",
        user=user, plan=items, status_counts=status_counts, platform_label=platform_label,
    )


@app.post("/plan")
def plan_submit(request: Request, days: int = Form(7), user: dict = Depends(current_user)):
    days = max(1, min(days, 14))
    description = user["description"] or "не указано"
    plan = content_gen.generate_content_plan(business_name_of(user), description, days)
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
        update_plan_status(user["id"], item_id, status)
        flash(request, "Статус пункта обновлён.")
    except ValueError:
        flash(request, "Недопустимый статус.")
    return RedirectResponse("/plan", status_code=303)


@app.post("/plan/{item_id}/delete")
def plan_item_delete(request: Request, item_id: int, user: dict = Depends(current_user)):
    delete_plan_item(user["id"], item_id)
    flash(request, "Пункт плана удалён.")
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
    delete_user_by_id(user["id"])
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# === ГЕНЕРАЦИЯ КАРТИНОК ===

@app.get("/images")
def images_gallery(request: Request, user: dict = Depends(current_user)):
    items = get_media_for_user(user["id"])
    return render(request, "images.html", user=user, images=items)


@app.get("/images/generate")
def image_generate_form(request: Request, user: dict = Depends(current_user)):
    return render(
        request, "image_generate.html",
        user=user, sizes=IMAGE_SIZES, styles=STYLE_PRESETS,
    )


@app.post("/images/generate")
def image_generate_submit(
    request: Request,
    prompt: str = Form(...),
    size: str = Form("square"),
    style: str = Form("none"),
    user: dict = Depends(current_user),
):
    prompt = prompt.strip()
    if not prompt:
        return render(
            request, "image_generate.html", status_code=400,
            user=user, sizes=IMAGE_SIZES, styles=STYLE_PRESETS,
            form={"prompt": prompt, "size": size, "style": style},
            errors=["Опиши, что нужно нарисовать."],
        )

    full_prompt = image_gen.build_prompt(prompt, style)
    try:
        image_bytes = image_gen.generate(full_prompt, size)
    except Exception as e:
        return render(
            request, "image_generate.html", status_code=502,
            user=user, sizes=IMAGE_SIZES, styles=STYLE_PRESETS,
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
