from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.types import Message, User

from config import Settings
from database import Database, SuggestedPost
from keyboards.moderation_inline import build_moderation_keyboard
from utils.formatters import format_moderation_card, normalize_text


logger = logging.getLogger(__name__)


async def check_rate_limit(
    *,
    database: Database,
    user_id: int,
    cooldown_seconds: int,
) -> tuple[bool, int]:
    last_created_at = await database.get_last_submission_created_at(user_id)
    if not last_created_at:
        return True, 0

    last_submission_time = datetime.fromisoformat(last_created_at)
    now = datetime.now(timezone.utc)
    wait_until = last_submission_time + timedelta(seconds=cooldown_seconds)

    if now >= wait_until:
        return True, 0

    return False, max(1, int((wait_until - now).total_seconds()))


async def create_submission(
    *,
    database: Database,
    user: User,
    original_text: str | None,
    file_id: str | None,
    signature: str | None,
    anonymous: bool,
) -> SuggestedPost:
    post_id = await database.create_post(
        user_id=user.id,
        username=user.username,
        first_name=user.full_name,
        original_text=original_text,
        final_text=original_text,
        signature=signature,
        base_signature=signature,
        anonymous=anonymous,
        base_anonymous=anonymous,
        file_id=file_id,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    await database.increment_user_submissions(user.id)
    post = await database.get_post(post_id)
    if post is None:
        raise RuntimeError("Post was created but could not be loaded back from database.")
    return post


async def deliver_submission_to_admin(
    *,
    bot: Bot,
    database: Database,
    settings: Settings,
    post: SuggestedPost,
) -> SuggestedPost:
    content_message = await send_raw_submission(
        bot=bot,
        chat_id=settings.admin_chat_id,
        text=normalize_text(post.original_text),
        file_id=post.file_id,
    )
    card_message = await bot.send_message(
        chat_id=settings.admin_chat_id,
        text=format_moderation_card(post, settings.timezone),
        reply_markup=build_moderation_keyboard(post),
        reply_to_message_id=content_message.message_id,
    )

    await database.set_admin_messages(
        post.id,
        content_message_id=content_message.message_id,
        card_message_id=card_message.message_id,
    )

    updated_post = await database.get_post(post.id)
    if updated_post is None:
        raise RuntimeError("Post disappeared after admin delivery.")
    return updated_post


async def send_raw_submission(
    *,
    bot: Bot,
    chat_id: int,
    text: str | None,
    file_id: str | None,
    reply_to_message_id: int | None = None,
) -> Message:
    if file_id:
        return await bot.send_photo(
            chat_id=chat_id,
            photo=file_id,
            caption=text,
            parse_mode=None,
            reply_to_message_id=reply_to_message_id,
        )

    if not text:
        raise ValueError("Text-only submission cannot be empty.")

    return await bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=None,
        reply_to_message_id=reply_to_message_id,
    )
