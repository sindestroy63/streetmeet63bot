from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest

from keyboards.moderation_inline import build_moderation_keyboard
from services.preview_service import send_preview
from services.publication_service import publish_submission
from utils.formatters import format_moderation_card


async def refresh_moderation_card(bot, settings, post) -> None:
    if not post or not post.moderation_chat_id or not post.moderation_message_id:
        return

    try:
        await bot.edit_message_text(
            chat_id=post.moderation_chat_id,
            message_id=post.moderation_message_id,
            text=format_moderation_card(post, settings.timezone),
            reply_markup=build_moderation_keyboard(post),
        )
    except TelegramBadRequest as error:
        message = str(error).lower()
        if "message is not modified" not in message:
            return
        try:
            await bot.edit_message_reply_markup(
                chat_id=post.moderation_chat_id,
                message_id=post.moderation_message_id,
                reply_markup=build_moderation_keyboard(post),
            )
        except TelegramBadRequest:
            return


async def preview_post(*, bot, database, settings, post_id: int) -> None:
    post = await database.get_submission(post_id)
    if not post:
        return
    await send_preview(bot, settings.admin_chat_id, post)


async def publish_post(*, bot, database, settings, post_id: int | None = None, post=None, moderator_id: int = 0, **_kwargs):
    target_post = post or (await database.get_submission(post_id)) if post_id is not None or post is not None else None
    if not target_post:
        return None

    await publish_submission(
        bot=bot,
        database=database,
        settings=settings,
        post=target_post,
        moderator_id=moderator_id,
        source_status=target_post.status,
    )

    refreshed = await database.get_submission(target_post.id)
    await refresh_moderation_card(bot, settings, refreshed)
    return refreshed


async def reject_post(*, bot, database, settings, post_id: int | None = None, post=None, moderator_id: int = 0, **_kwargs):
    target_post = post or (await database.get_submission(post_id)) if post_id is not None or post is not None else None
    if not target_post:
        return None

    await database.reject_post(target_post.id, moderator_id=moderator_id)
    refreshed = await database.get_submission(target_post.id)
    await refresh_moderation_card(bot, settings, refreshed)
    return refreshed


async def toggle_anonymous(*, bot, database, settings, post_id: int) -> None:
    post = await database.get_submission(post_id)
    if not post:
        return
    await database.set_anonymous(post_id=post.id, anonymous=not bool(post.anonymous))
    refreshed = await database.get_submission(post.id)
    await refresh_moderation_card(bot, settings, refreshed)


async def reset_post(*, bot, database, settings, post_id: int) -> None:
    await database.reset_post(post_id)
    refreshed = await database.get_submission(post_id)
    await refresh_moderation_card(bot, settings, refreshed)


async def clear_signature(*, bot, database, settings, post_id: int) -> None:
    await database.update_signature(post_id=post_id, signature="")
    await database.set_admin_signature(post_id=post_id, is_admin_signature=False)
    refreshed = await database.get_submission(post_id)
    await refresh_moderation_card(bot, settings, refreshed)


async def update_text(*, bot, database, settings, post_id: int, text: str) -> None:
    await database.update_final_text(post_id=post_id, final_text=text)
    refreshed = await database.get_submission(post_id)
    await refresh_moderation_card(bot, settings, refreshed)


async def update_signature(*, bot, database, settings, post_id: int, signature: str) -> None:
    await database.update_signature(post_id=post_id, signature=signature)
    await database.set_admin_signature(post_id=post_id, is_admin_signature=bool(signature))
    if signature:
        await database.set_anonymous(post_id=post_id, anonymous=False)
    refreshed = await database.get_submission(post_id)
    await refresh_moderation_card(bot, settings, refreshed)
