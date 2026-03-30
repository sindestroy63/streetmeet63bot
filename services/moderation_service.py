from __future__ import annotations

import logging

from aiogram import Bot

from keyboards.moderation_inline import build_moderation_keyboard
from services.publication_service import publish_submission
from utils.formatters import build_signature_variants, format_moderation_card

logger = logging.getLogger(__name__)


async def refresh_moderation_card(bot: Bot, settings, post) -> None:
    card_chat_id = getattr(post, "admin_card_chat_id", None) or getattr(post, "card_chat_id", None)
    card_message_id = getattr(post, "admin_card_message_id", None) or getattr(post, "card_message_id", None)

    if not card_chat_id or not card_message_id:
        return

    try:
        await bot.edit_message_caption(
            chat_id=card_chat_id,
            message_id=card_message_id,
            caption=format_moderation_card(post, settings.timezone),
            reply_markup=build_moderation_keyboard(post),
        )
    except Exception:
        try:
            await bot.edit_message_text(
                chat_id=card_chat_id,
                message_id=card_message_id,
                text=format_moderation_card(post, settings.timezone),
                reply_markup=build_moderation_keyboard(post),
            )
        except Exception as error:
            logger.warning(
                "Failed to refresh moderation card chat_id=%s message_id=%s post_id=%s: %s",
                card_chat_id,
                card_message_id,
                getattr(post, "id", None),
                error,
            )
            return


async def notify_user(bot: Bot, post, text: str) -> None:
    user_id = getattr(post, "user_id", None)
    if not user_id:
        return
    try:
        await bot.send_message(chat_id=user_id, text=text)
    except Exception:
        return


async def toggle_anonymous(*, bot: Bot, database, settings, post_id: int | None = None, post=None, **_kwargs):
    resolved_post = post or (await database.get_post(post_id)) if post_id is not None else post
    if resolved_post is None:
        return False, "Заявка не найдена."

    await database.set_anonymous(resolved_post.id, not resolved_post.anonymous)
    updated_post = await database.get_post(resolved_post.id)
    if updated_post is not None:
        await refresh_moderation_card(bot, settings, updated_post)
    return True, "Режим анонимности обновлён."


async def reset_post(*, bot: Bot, database, settings, post_id: int | None = None, post=None, **_kwargs):
    resolved_post = post or (await database.get_post(post_id)) if post_id is not None else post
    if resolved_post is None:
        return False, "Заявка не найдена."

    await database.reset_post(resolved_post.id)
    updated_post = await database.get_post(resolved_post.id)
    if updated_post is not None:
        await refresh_moderation_card(bot, settings, updated_post)
    return True, "Изменения сброшены."


async def apply_signature_variant(
    *,
    bot: Bot,
    database,
    settings,
    post_id: int | None = None,
    post=None,
    variant: str,
    **_kwargs,
):
    resolved_post = post or (await database.get_post(post_id)) if post_id is not None else post
    if resolved_post is None:
        return False, "Заявка не найдена."

    variants = build_signature_variants(resolved_post)
    signature = variants.get(variant)
    if signature is None:
        return False, "Неизвестный тип подписи."

    await database.set_anonymous(resolved_post.id, False)
    await database.set_admin_signature(resolved_post.id, False)
    await database.update_signature(resolved_post.id, signature)
    updated_post = await database.get_post(resolved_post.id)
    if updated_post is not None:
        await refresh_moderation_card(bot, settings, updated_post)
    return True, "Подпись обновлена."


async def clear_signature(*, bot: Bot, database, settings, post_id: int | None = None, post=None, **_kwargs):
    resolved_post = post or (await database.get_post(post_id)) if post_id is not None else post
    if resolved_post is None:
        return False, "Заявка не найдена."

    await database.update_signature(resolved_post.id, None)
    await database.set_admin_signature(resolved_post.id, False)
    updated_post = await database.get_post(resolved_post.id)
    if updated_post is not None:
        await refresh_moderation_card(bot, settings, updated_post)
    return True, "Подпись удалена."


async def update_text(
    *,
    bot: Bot,
    database,
    settings,
    post_id: int | None = None,
    post=None,
    text: str | None = None,
    **_kwargs,
):
    resolved_post = post or (await database.get_post(post_id)) if post_id is not None else post
    if resolved_post is None:
        return False, "Заявка не найдена."

    await database.update_final_text(resolved_post.id, text)
    updated_post = await database.get_post(resolved_post.id)
    if updated_post is not None:
        await refresh_moderation_card(bot, settings, updated_post)
    return True, "Текст обновлён."


async def update_signature(
    *,
    bot: Bot,
    database,
    settings,
    post_id: int | None = None,
    post=None,
    signature: str | None = None,
    **_kwargs,
):
    resolved_post = post or (await database.get_post(post_id)) if post_id is not None else post
    if resolved_post is None:
        return False, "Заявка не найдена."

    await database.update_signature(resolved_post.id, signature)
    updated_post = await database.get_post(resolved_post.id)
    if updated_post is not None:
        await refresh_moderation_card(bot, settings, updated_post)
    return True, "Подпись обновлена."


async def publish_post(
    *,
    bot: Bot,
    database,
    settings,
    post_id: int | None = None,
    post=None,
    moderator_id: int = 0,
    **_kwargs,
):
    resolved_post = post or (await database.get_post(post_id)) if post_id is not None else post
    if resolved_post is None:
        return False, "Заявка не найдена."

    source_status = "scheduled" if getattr(resolved_post, "status", None) == "scheduled" else "pending"
    ok, result_text = await publish_submission(
        bot=bot,
        database=database,
        settings=settings,
        post=resolved_post,
        moderator_id=moderator_id,
        source_status=source_status,
    )

    updated_post = await database.get_post(resolved_post.id)
    if updated_post is not None:
        await refresh_moderation_card(bot, settings, updated_post)

    return ok, result_text


async def reject_post(
    *,
    bot: Bot,
    database,
    settings,
    post_id: int | None = None,
    post=None,
    moderator_id: int = 0,
    **_kwargs,
):
    resolved_post = post or (await database.get_post(post_id)) if post_id is not None else post
    if resolved_post is None:
        return False, "Заявка не найдена."

    changed = await database.reject_post(resolved_post.id, moderator_id)
    if not changed:
        return False, "Заявка уже обработана."

    updated_post = await database.get_post(resolved_post.id)
    if updated_post is not None:
        await refresh_moderation_card(bot, settings, updated_post)

    return True, "Заявка отклонена."
