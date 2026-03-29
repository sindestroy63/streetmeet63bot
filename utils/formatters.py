from __future__ import annotations

from html import escape

from database import SuggestedPost
from utils.datetime_utils import format_datetime_display


def normalize_text(text: str | None) -> str | None:
    if text is None:
        return None
    cleaned = text.replace("\r\n", "\n").strip()
    return cleaned or None


def truncate_text(text: str | None, limit: int = 500) -> str:
    normalized = normalize_text(text)
    if not normalized:
        return "—"
    if len(normalized) <= limit:
        return escape(normalized)
    return f"{escape(normalized[: limit - 3])}..."


def format_status(status: str) -> str:
    mapping = {
        "pending": "На модерации",
        "scheduled": "Запланирован",
        "publishing": "Публикуется",
        "published": "Опубликован",
        "rejected": "Отклонён",
    }
    return mapping.get(status, status)


def content_type_label(post: SuggestedPost) -> str:
    if post.file_id and normalize_text(post.original_text):
        return "Фото + текст"
    if post.file_id:
        return "Фото"
    return "Текст"


def author_label(post: SuggestedPost) -> str:
    if post.username and post.first_name:
        return f"{escape(post.first_name)} (@{escape(post.username)})"
    if post.username:
        return f"@{escape(post.username)}"
    if post.first_name:
        return f"{escape(post.first_name)} | ID {post.user_id}"
    return f"ID {post.user_id}"


def short_author_handle(post: SuggestedPost) -> str:
    if post.username:
        return f"@{post.username}"
    if post.first_name:
        compact = " ".join(post.first_name.split())
        return compact[:14] if len(compact) <= 14 else f"{compact[:13]}…"
    return f"ID {post.user_id}"


def build_default_author_signature(
    *,
    user_id: int,
    username: str | None,
    first_name: str | None,
) -> str:
    if username:
        return f"от @{username}"
    if normalize_text(first_name):
        return f"от {normalize_text(first_name)}"
    return f"ID автора: {user_id}"


def build_signature_variants(post: SuggestedPost) -> dict[str, str]:
    base = short_author_handle(post)
    return {
        "user": base,
        "from_user": f"от {base}",
        "user_id": f"ID автора: {post.user_id}",
        "user_button": base,
        "from_user_button": f"от {base}",
    }


def compose_publication_text(post: SuggestedPost) -> str | None:
    final_text = normalize_text(post.final_text if post.final_text is not None else post.original_text)
    signature = None if post.anonymous else normalize_text(post.signature)
    parts = [part for part in (final_text, signature) if part]
    if not parts:
        return None
    return "\n\n".join(parts)


def publication_mode_label(post: SuggestedPost) -> str:
    if post.anonymous:
        return "анонимно"
    if post.username:
        return f"@{escape(post.username)}"
    if normalize_text(post.first_name):
        return escape(normalize_text(post.first_name))
    return f"ID {post.user_id}"


def publication_timing_label(post: SuggestedPost, tzinfo) -> str:
    if post.status == "scheduled" and post.scheduled_at:
        return format_datetime_display(post.scheduled_at, tzinfo)
    if post.status == "published":
        return format_datetime_display(post.published_at or post.scheduled_at, tzinfo)
    if post.status == "rejected":
        return "—"
    return "сразу"


def format_moderation_card(post: SuggestedPost, tzinfo) -> str:
    return (
        f"<b>Заявка #{post.id}</b>\n\n"
        f"<b>Автор:</b> {author_label(post)}\n"
        f"<b>Тип:</b> {content_type_label(post)}\n"
        f"<b>Статус:</b> {format_status(post.status)}\n"
        f"<b>Публикация:</b> {publication_timing_label(post, tzinfo)}\n"
        f"<b>Формат автора:</b> {publication_mode_label(post)}\n"
        f"<b>Создано:</b> {format_datetime_display(post.created_at, tzinfo)}\n\n"
        f"<b>Текст:</b>\n{truncate_text(post.final_text, 700)}\n\n"
        f"<b>Подпись:</b>\n{truncate_text(post.signature, 300)}"
    )
