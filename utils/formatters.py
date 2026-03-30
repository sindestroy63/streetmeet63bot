from __future__ import annotations

import html
from datetime import datetime


def normalize_text(value: str | None) -> str:
    return (value or "").strip()


def truncate_text(value: str | None, limit: int = 40) -> str:
    text = normalize_text(value)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def format_status(status: str) -> str:
    mapping = {
        "pending": "На модерации",
        "scheduled": "Запланирован",
        "published": "Опубликован",
        "rejected": "Отклонён",
    }
    return mapping.get(status, status)


def content_type_label(post) -> str:
    media_type = normalize_text(getattr(post, "media_type", ""))
    has_media = bool(getattr(post, "file_id", ""))
    has_text = bool(normalize_text(getattr(post, "final_text", None) or getattr(post, "original_text", None)))
    if media_type == "video" and has_text:
        return "Видео + текст"
    if media_type == "video":
        return "Видео"
    if has_media and has_text:
        return "Фото + текст"
    if has_media:
        return "Фото"
    return "Текст"


def author_label(post) -> str:
    username = normalize_text(getattr(post, "username", ""))
    first_name = normalize_text(getattr(post, "first_name", ""))
    user_id = getattr(post, "user_id", 0)
    if username:
        if first_name:
            return f"{html.escape(first_name)} (@{html.escape(username)})"
        return f"@{html.escape(username)}"
    if first_name:
        return f"{html.escape(first_name)} (ID {user_id})"
    return f"ID {user_id}"


def short_author_handle(post) -> str:
    username = normalize_text(getattr(post, "username", ""))
    first_name = normalize_text(getattr(post, "first_name", ""))
    user_id = getattr(post, "user_id", 0)
    if username:
        return f"@{username}"
    if first_name:
        return first_name
    return f"ID {user_id}"


def build_default_author_signature(post=None, **kwargs) -> str:
    username = normalize_text(kwargs.get("username"))
    first_name = normalize_text(kwargs.get("first_name"))
    user_id = kwargs.get("user_id")

    if post is not None:
        username = normalize_text(getattr(post, "username", username))
        first_name = normalize_text(getattr(post, "first_name", first_name))
        user_id = getattr(post, "user_id", user_id)

    if username:
        return f"@{username}"
    if first_name:
        return first_name
    if user_id:
        return f"ID {user_id}"
    return ""


def build_signature_variants(post) -> dict[str, str]:
    base = build_default_author_signature(post)
    user_id = getattr(post, "user_id", 0)
    variants = {
        "username": base if base else f"ID {user_id}",
        "from_username": f"от {base}" if base else f"от ID {user_id}",
        "author_id": f"ID {user_id}",
    }
    return variants


def compose_publication_text(post) -> str:
    text = normalize_text(getattr(post, "final_text", None) or getattr(post, "original_text", None))
    signature = normalize_text(getattr(post, "signature", ""))
    anonymous = bool(getattr(post, "anonymous", False))
    is_admin_signature = bool(getattr(post, "is_admin_signature", False))

    if anonymous:
        return text

    if signature and is_admin_signature:
        signature = f"admin: {signature}"

    parts = [part for part in (text, signature) if part]
    return "\n\n".join(parts)


def publication_mode_label(post) -> str:
    return "анонимно" if getattr(post, "anonymous", False) else "обычно"


def anonymity_label(post) -> str:
    return "включена" if getattr(post, "anonymous", False) else "выключена"


def signature_mode_label(post) -> str:
    signature = normalize_text(getattr(post, "signature", ""))
    if not signature:
        return "без подписи"
    if getattr(post, "is_admin_signature", False):
        return "admin"
    return "обычная"


def publication_timing_label(post, tzinfo) -> str:
    status = getattr(post, "status", "")
    scheduled_at = getattr(post, "scheduled_at", None)
    published_at = getattr(post, "published_at", None)

    if status == "scheduled" and scheduled_at:
        return _format_datetime(scheduled_at, tzinfo)
    if status == "published" and published_at:
        return _format_datetime(published_at, tzinfo)
    return "сразу"


def _format_datetime(value, tzinfo) -> str:
    if not value:
        return "—"

    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tzinfo)
    else:
        dt = dt.astimezone(tzinfo)
    return dt.strftime("%d.%m.%Y %H:%M")


def format_moderation_card(post, tzinfo) -> str:
    status = format_status(getattr(post, "status", "pending"))
    timing = publication_timing_label(post, tzinfo)
    author = author_label(post)
    content_type = content_type_label(post)
    created_at = _format_datetime(getattr(post, "created_at", None), tzinfo)

    text = normalize_text(getattr(post, "final_text", None) or getattr(post, "original_text", None))
    signature = normalize_text(getattr(post, "signature", ""))

    text_block = html.escape(text) if text else "—"
    if signature:
        if getattr(post, "is_admin_signature", False):
            signature_block = f"admin: {html.escape(signature)}"
        else:
            signature_block = html.escape(signature)
    else:
        signature_block = "—"

    return (
        f"<b>Заявка #{post.id}</b>\n\n"
        f"<b>Автор:</b> {author}\n"
        f"<b>Тип:</b> {content_type}\n"
        f"<b>Статус:</b> {status}\n"
        f"<b>Публикация:</b> {timing}\n"
        f"<b>Анонимность:</b> {anonymity_label(post)}\n"
        f"<b>Режим подписи:</b> {signature_mode_label(post)}\n"
        f"<b>Создано:</b> {created_at}\n\n"
        f"<b>Текст:</b>\n{text_block}\n\n"
        f"<b>Подпись:</b>\n{signature_block}"
    )
