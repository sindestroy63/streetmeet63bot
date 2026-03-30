from __future__ import annotations

from datetime import datetime

from keyboards.moderation_main import build_moderation_main_keyboard
from services.preview_service import send_media_content
from utils.formatters import build_default_author_signature, format_moderation_card


async def check_rate_limit(database, settings, user_id: int) -> tuple[bool, int]:
    last_created_at = await database.get_last_submission_created_at(user_id)
    if not last_created_at:
        return True, 0

    last_dt = datetime.fromisoformat(last_created_at.replace("Z", "+00:00"))
    now = datetime.now(settings.timezone)
    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=settings.timezone)
    else:
        last_dt = last_dt.astimezone(settings.timezone)

    seconds_passed = int((now - last_dt).total_seconds())
    remaining = settings.submission_cooldown_seconds - seconds_passed
    return remaining <= 0, max(0, remaining)


async def create_submission(database, user, file_id: str, text: str, publish_as_author: bool, media_type: str = ""):
    signature = build_default_author_signature(username=user.username, first_name=user.first_name, user_id=user.telegram_id) if publish_as_author else ""
    post = await database.create_submission(
        user_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        original_text=text or "",
        final_text=text or "",
        signature=signature,
        base_signature=signature,
        anonymous=not publish_as_author,
        base_anonymous=not publish_as_author,
        is_admin_signature=False,
        file_id=file_id or "",
        media_type=media_type or "",
        status="pending",
    )
    await database.increment_user_submissions(user.telegram_id)
    return await database.get_submission(post.id)


async def deliver_submission_to_admin(bot, database, settings, post) -> None:
    source_message = await send_media_content(
        bot,
        settings.admin_chat_id,
        file_id=post.file_id,
        media_type=post.media_type,
        text=post.final_text or "",
    )

    card_message = await bot.send_message(
        chat_id=settings.admin_chat_id,
        text=format_moderation_card(post, settings.timezone),
        reply_markup=build_moderation_main_keyboard(post),
    )

    await database.set_admin_messages(
        post_id=post.id,
        source_chat_id=source_message.chat.id if source_message else None,
        source_message_id=source_message.message_id if source_message else None,
        card_chat_id=card_message.chat.id,
        card_message_id=card_message.message_id,
    )
