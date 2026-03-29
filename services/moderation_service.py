from __future__ import annotations

import logging
from contextlib import suppress

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from config import Settings
from database import Database, SuggestedPost
from keyboards.moderation_inline import build_moderation_keyboard
from services.publication_service import publish_submission
from utils.formatters import build_signature_variants, format_moderation_card


logger = logging.getLogger(__name__)


async def refresh_moderation_card(bot: Bot, settings: Settings, post: SuggestedPost) -> None:
    if not post.admin_card_message_id:
        return

    try:
        await bot.edit_message_text(
            chat_id=settings.admin_chat_id,
            message_id=post.admin_card_message_id,
            text=format_moderation_card(post, settings.timezone),
            reply_markup=build_moderation_keyboard(post),
        )
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return
        raise


async def toggle_anonymous(
    *,
    database: Database,
    bot: Bot,
    settings: Settings,
    post: SuggestedPost,
) -> SuggestedPost | None:
    changed = await database.set_anonymous(post.id, not post.anonymous)
    if not changed:
        return None
    updated_post = await database.get_post(post.id)
    if updated_post:
        await refresh_moderation_card(bot, settings, updated_post)
    return updated_post


async def reset_post(
    *,
    database: Database,
    bot: Bot,
    settings: Settings,
    post: SuggestedPost,
) -> SuggestedPost | None:
    changed = await database.reset_post(post.id)
    if not changed:
        return None
    updated_post = await database.get_post(post.id)
    if updated_post:
        await refresh_moderation_card(bot, settings, updated_post)
    return updated_post


async def apply_signature_variant(
    *,
    database: Database,
    bot: Bot,
    settings: Settings,
    post: SuggestedPost,
    variant_key: str,
) -> SuggestedPost | None:
    signature = build_signature_variants(post)[variant_key]
    changed = await database.update_signature(post.id, signature)
    if not changed:
        return None
    updated_post = await database.get_post(post.id)
    if updated_post:
        await refresh_moderation_card(bot, settings, updated_post)
    return updated_post


async def clear_signature(
    *,
    database: Database,
    bot: Bot,
    settings: Settings,
    post: SuggestedPost,
) -> SuggestedPost | None:
    changed = await database.update_signature(post.id, None)
    if not changed:
        return None
    updated_post = await database.get_post(post.id)
    if updated_post:
        await refresh_moderation_card(bot, settings, updated_post)
    return updated_post


async def update_text(
    *,
    database: Database,
    bot: Bot,
    settings: Settings,
    post_id: int,
    new_text: str | None,
) -> SuggestedPost | None:
    changed = await database.update_final_text(post_id, new_text)
    if not changed:
        return None
    updated_post = await database.get_post(post_id)
    if updated_post:
        await refresh_moderation_card(bot, settings, updated_post)
    return updated_post


async def update_signature(
    *,
    database: Database,
    bot: Bot,
    settings: Settings,
    post_id: int,
    new_signature: str | None,
) -> SuggestedPost | None:
    changed = await database.update_signature(post_id, new_signature)
    if not changed:
        return None
    updated_post = await database.get_post(post_id)
    if updated_post:
        await refresh_moderation_card(bot, settings, updated_post)
    return updated_post


async def publish_post(
    *,
    database: Database,
    bot: Bot,
    settings: Settings,
    post: SuggestedPost,
    moderator_id: int,
) -> tuple[bool, str]:
    source_status = "scheduled" if post.status == "scheduled" else "pending"
    ok, result_text = await publish_submission(
        database=database,
        bot=bot,
        settings=settings,
        post=post,
        moderator_id=moderator_id,
        source_status=source_status,
    )
    if not ok:
        refreshed = await database.get_post(post.id)
        if refreshed:
            await refresh_moderation_card(bot, settings, refreshed)
        return False, result_text

    updated_post = await database.get_post(post.id)
    if updated_post:
        await refresh_moderation_card(bot, settings, updated_post)
        await notify_user(bot, updated_post.user_id, "Ваша предложка опубликована.")
    return True, result_text


async def reject_post(
    *,
    database: Database,
    bot: Bot,
    settings: Settings,
    post: SuggestedPost,
    moderator_id: int,
) -> tuple[bool, str]:
    changed = await database.mark_rejected(post.id, moderator_id)
    if not changed:
        return False, "Заявка уже обработана."

    updated_post = await database.get_post(post.id)
    if updated_post:
        await refresh_moderation_card(bot, settings, updated_post)
        await notify_user(bot, updated_post.user_id, "Ваша предложка отклонена.")
    return True, "Заявка отклонена."


async def notify_user(bot: Bot, user_id: int, text: str) -> None:
    with suppress(TelegramForbiddenError, TelegramBadRequest):
        await bot.send_message(user_id, text, parse_mode=None)
