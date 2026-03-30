from __future__ import annotations

from datetime import datetime, timedelta, timezone

from keyboards.moderation_inline import build_moderation_keyboard
from services.preview_service import send_rendered_post
from utils.formatters import build_default_author_signature, format_moderation_card


async def check_rate_limit(database, settings, user_id: int) -> tuple[bool, int]:
    last_created_at = await database.get_last_submission_created_at(user_id)
    if not last_created_at:
        return True, 0

    try:
        last_dt = datetime.fromisoformat(last_created_at)
    except ValueError:
        return True, 0

    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    wait_until = last_dt + timedelta(seconds=settings.submission_cooldown_seconds)
    if now >= wait_until:
        return True, 0

    wait_seconds = int((wait_until - now).total_seconds())
    return False, max(wait_seconds, 1)


async def create_submission(
    database,
    user,
    file_id: str | None,
    text: str | None,
    publish_as_author: bool,
):
    signature = None
    anonymous = not publish_as_author

    if publish_as_author:
        signature = build_default_author_signature(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
        )

    return await database.create_submission(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        original_text=text,
        final_text=text,
        file_id=file_id,
        signature=signature,
        base_signature=signature,
        is_admin_signature=False,
        base_admin_signature=False,
        anonymous=anonymous,
        base_anonymous=anonymous,
        status="pending",
    )


async def deliver_submission_to_admin(bot, database, settings, post) -> None:
    content_text = post.final_text or post.original_text
    message_ids = await send_rendered_post(
        bot=bot,
        chat_id=settings.admin_chat_id,
        file_id=post.file_id,
        text=content_text,
        reply_markup=None,
    )
    source_message_id = message_ids[0] if message_ids else None

    card_message = await bot.send_message(
        chat_id=settings.admin_chat_id,
        text=format_moderation_card(post, settings.timezone),
        reply_markup=build_moderation_keyboard(post),
    )

    await database.set_admin_messages(
        post_id=post.id,
        content_chat_id=settings.admin_chat_id,
        content_message_id=source_message_id,
        moderation_chat_id=settings.admin_chat_id,
        moderation_message_id=card_message.message_id,
    )
