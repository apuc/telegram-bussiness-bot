"""Проверка адресов, к которым сервер ходит по указанию пользователя (свой ИИ-провайдер, ссылки на картинки).
Без неё через «свой провайдер» можно заставить сервер обратиться во внутреннюю сеть (SSRF)."""
import ipaddress
import socket
from urllib.parse import urlparse


def public_url_error(url: str, allow_http: bool = False):
    """None — адрес публичный и допустимый, иначе текст ошибки для пользователя."""
    try:
        parsed = urlparse((url or "").strip())
    except ValueError:
        return "Некорректный адрес."
    schemes = ("https", "http") if allow_http else ("https",)
    if parsed.scheme not in schemes:
        return "Адрес должен начинаться с https://."
    host = parsed.hostname
    if not host:
        return "В адресе нет домена."
    try:
        infos = socket.getaddrinfo(host, parsed.port or 443, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError):
        return f"Домен {host} не найден."
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if not ip.is_global or ip.is_multicast:
            return f"Адрес {host} ведёт во внутреннюю сеть — такие адреса запрещены."
    return None


def is_public_url(url: str) -> bool:
    return public_url_error(url) is None
