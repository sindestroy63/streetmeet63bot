from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest

from keyboards.post_actions import build_post_actions_keyboard
from services.preview_service import send_rendered_post


def _channel_targets(settings) -> list[int | str]:
    targets: list[int | str] = []
    if getattr(settings, "channel_id", None):
        targets.append(settings.channel_id)

    channel_url = (getattr(settings, "channel_url", "") or "").strip()
    if "t.me/" in channel_url:
        username = channel_url.rsplit("/", 1)[-1].strip().removeprefix("@")
        if username:
            handle = f"@{username}"
            if handle not in targets:
                targets.append(handle)
    return targets


async def publish_submission(bot, database, settings, post, moderator_id: int | None = None):
    if not await database.start_publication(post.id):
        return None

    previous_status = post.status
    last_error = None

    try:
        target_message = None
        for target in _channel_targets(settings):
            try:
                target_message = await send_rendered_post(
                    bot,
                    target,
                    post,
                    reply_markup=build_post_actions_keyboard(),
                )
                break
            except TelegramBadRequest as error:
                last_error = error
                if "chat not found" not in str(error).lower():
                    raise

        if target_message is None:
            raise last_error or RuntimeError("Unable to publish post")

        await database.finish_publication(post.id, moderator_id=moderator_id)
        await database.set_admin_messages(
            post_id=post.id,
            source_chat_id=target_message.chat.id,
            source_message_id=target_message.message_id,
        )
        return target_message
    except Exception:
        await database.rollback_publication(post.id, previous_status=previous_status)
        raise
