"""Публикация постов в TenChat через внутренний API.

TenChat — SPA на Nuxt, API-префикс /gostinder/api/web/auth/...
Авторизация через Bearer-токен (access_token), получаемый через refresh.

Механизм аутентификации:
  1. POST /tenchat-oauth2/oauth/token?refresh_token={TCRF}&grant_type=refresh_token
     → возвращает access_token + новый refresh_token (TCRF одноразовый!)
  2. API-запросы с заголовком Authorization: Bearer {access_token}

API-поток публикации (изучен через редактор tenchat.ru/editor):
  1. POST /gostinder/api/web/auth/user/post/draft
     — создать черновик, получаем числовой draft_id
  2. PUT  /gostinder/api/web/auth/user/post/draft/publish/id/{draft_id}
     — опубликовать
  3. GET  /gostinder/api/web/auth/post/id/{draft_id}
     — получить данные поста (draft_id == post_id после публикации)
"""

import json
import re

import requests

TENCHAT_BASE = "https://tenchat.ru"
REFRESH_ENDPOINT = "/tenchat-oauth2/oauth/token"
DRAFT_ENDPOINT = "/gostinder/api/web/auth/user/post/draft"
DRAFT_PUBLISH_ENDPOINT = "/gostinder/api/web/auth/user/post/draft/publish/id/{draft_id}"
POST_GET_ENDPOINT = "/gostinder/api/web/auth/post/id/{post_id}"

# Заголовки, имитирующие браузер
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    "Content-Type": "application/json",
    "Origin": TENCHAT_BASE,
    "Referer": TENCHAT_BASE + "/",
}


def refresh_access_token(tcrf: str) -> dict:
    """Обновляет access_token через refresh_token (TCRF).
    
    TCRF — одноразовый! После использования он заменяется новым.
    
    Возвращает dict с access_token, refresh_token (новый TCRF), expires_in.
    При ошибке — dict с error.
    """
    url = f"{TENCHAT_BASE}{REFRESH_ENDPOINT}?refresh_token={tcrf}&grant_type=refresh_token"
    try:
        resp = requests.post(url, headers=DEFAULT_HEADERS, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
                "expires_in": data.get("expires_in"),
            }
        return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def _request(method, url, access_token, json_body=None, timeout=30):
    """Выполняет запрос к TenChat API с Bearer-токеном.
    
    Возвращает (ok, data_or_error).
    """
    headers = {**DEFAULT_HEADERS, "Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.request(
            method, url, json=json_body, headers=headers, timeout=timeout
        )
        try:
            data = resp.json()
        except ValueError:
            data = resp.text

        if resp.status_code in (200, 201):
            return True, data
        return False, {"status": resp.status_code, "body": data}
    except Exception as e:
        return False, {"error": str(e)}


def _build_draft_body(text: str, tags=None):
    """Собирает тело запроса для создания черновика."""
    return {
        "adminTagTechNames": [],
        "attachments": [],
        "metadata": "",
        "pictures": [],
        "picturesDto": [],
        "tagCodes": tags or [],
        "text": text,
        "title": "",
        "videos": [],
        "videosDto": [],
    }


def create_draft(access_token: str, text: str, tags=None):
    """Создаёт черновик поста в TenChat."""
    body = _build_draft_body(text, tags)
    url = TENCHAT_BASE + DRAFT_ENDPOINT
    ok, data = _request("POST", url, access_token, json_body=body)
    if not ok:
        return False, data

    draft_id = None
    if isinstance(data, dict):
        draft_id = data.get("id") or data.get("draftId")
    elif isinstance(data, (int, float)):
        draft_id = int(data)
    elif isinstance(data, str):
        m = re.search(r"(\d+)", data)
        if m:
            draft_id = m.group(1)

    if not draft_id:
        return False, {"error": "Не удалось получить draft_id", "body": data}
    return True, draft_id


def publish_draft(access_token: str, draft_id):
    """Публикует черновик поста в TenChat."""
    url = TENCHAT_BASE + DRAFT_PUBLISH_ENDPOINT.format(draft_id=draft_id)
    return _request("PUT", url, access_token)


def get_post(access_token: str, post_id):
    """Получает данные поста по ID."""
    url = TENCHAT_BASE + POST_GET_ENDPOINT.format(post_id=post_id)
    return _request("GET", url, access_token)


def publish_post(tcrf: str, text: str, tags=None):
    """Полный цикл публикации поста в TenChat.
    
    Принимает TCRF (refresh token).
    Возвращает (ok, result_or_error, new_tcrf).
    new_tcrf — новый refresh_token для сохранения в БД.
    """
    # 1. Получаем access_token через refresh
    refresh_result = refresh_access_token(tcrf)
    if "error" in refresh_result:
        return False, refresh_result, None
    
    access_token = refresh_result["access_token"]
    new_tcrf = refresh_result["refresh_token"]
    
    # 2. Создаём черновик
    ok, draft_id = create_draft(access_token, text, tags)
    if not ok:
        return False, draft_id, new_tcrf
    
    # 3. Публикуем
    ok, result = publish_draft(access_token, draft_id)
    if not ok:
        return False, result, new_tcrf
    
    # 4. Получаем post_id
    post_id = draft_id
    ok, post_data = get_post(access_token, draft_id)
    if ok and isinstance(post_data, dict):
        post_id = post_data.get("id") or post_id
    
    return True, {
        "post_id": post_id,
        "url": f"{TENCHAT_BASE}/post/{post_id}" if post_id else None,
        "draft_id": draft_id,
    }, new_tcrf
