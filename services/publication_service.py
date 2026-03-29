from __future__ import annotations

from datetime import datetime

from aiogram import Bot

from config import Settings
from database import Database, SuggestedPost
from services.preview_service import send_rendered_post
from utils.formatters import compose_publication_text


async def publish_submission(
    *,
    database: Database,
    bot: Bot,
    settings: Settings,
    post: SuggestedPost,
    moderator_id: int | None,
    source_status: str,
) -> tuple[bool, str]:
    rendered_text = compose_publication_text(post)
    if not post.file_id and not rendered_text:
        return False, "Нельзя опубликовать пустой текстовый пост."

    if source_status == "scheduled" and moderator_id is None:
        claimed = await database.claim_scheduled_post(post.id)
    else:
        claimed = await database.start_publication(post.id, moderator_id or 0)

    if not claimed:
        return False, "Заявка уже обработана."

    try:
        await send_rendered_post(
            bot=bot,
            chat_id=settings.channel_id,
            file_id=post.file_id,
            text=rendered_text,
        )
    except Exception:
        await database.rollback_publication(post.id, restore_status=source_status)
        return False, "Не удалось опубликовать. Проверьте CHANNEL_ID и права бота."

    await database.finish_publication(post.id, published_at=_now_iso(settings))
    return True, "Пост опубликован."


def _now_iso(settings: Settings) -> str:
    return datetime.now(settings.timezone).isoformat()
