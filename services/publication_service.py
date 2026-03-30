from __future__ import annotations

from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from config import Settings
from database import Database, SuggestedPost
from keyboards.post_actions import build_post_actions_keyboard
from services.preview_service import send_rendered_post
from utils.formatters import compose_publication_text


def _now_iso(settings: Settings) -> str:
    return datetime.now(settings.timezone).isoformat()


def _extract_public_channel_username(channel_url: str | None) -> str | None:
    value = (channel_url or "").strip()
    if not value:
        return None

    if "t.me/" in value:
        value = value.split("t.me/", maxsplit=1)[1]

    value = value.strip().strip("/")
    if not value or value.startswith("+"):
        return None

    return value if value.startswith("@") else f"@{value}"


def _publication_targets(settings: Settings) -> list[int | str]:
    targets: list[int | str] = [settings.channel_id]
    public_username = _extract_public_channel_username(settings.channel_url)
    if public_username and public_username != settings.channel_id:
        targets.append(public_username)
    return targets


async def publish_submission(
    bot: Bot,
    database: Database,
    settings: Settings,
    post: SuggestedPost,
    moderator_id: int | None,
    source_status: str | None = None,
) -> tuple[bool, str]:
    current_status = source_status or post.status
    publication_text = compose_publication_text(post)

    if current_status == "scheduled" and moderator_id is None:
        claimed = await database.claim_scheduled_post(post.id)
    else:
        claimed = await database.start_publication(post.id, moderator_id or 0)

    if not claimed:
        return False, "Заявка уже обработана или недоступна для публикации."

    try:
        last_error: Exception | None = None

        for target_chat in _publication_targets(settings):
            try:
                await send_rendered_post(
                    bot=bot,
                    chat_id=target_chat,
                    file_id=post.file_id,
                    text=publication_text,
                    reply_markup=build_post_actions_keyboard(),
                )
                last_error = None
                break
            except TelegramBadRequest as error:
                if "chat not found" in str(error).lower():
                    last_error = error
                    continue
                raise

        if last_error is not None:
            raise last_error
    except Exception:
        await database.rollback_publication(post.id, restore_status=current_status)
        raise

    await database.finish_publication(post.id, published_at=_now_iso(settings))
    return True, "Пост опубликован."
