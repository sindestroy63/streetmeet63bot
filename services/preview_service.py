from __future__ import annotations

from aiogram import Bot
from aiogram.types import Message

from database import SuggestedPost
from utils.formatters import compose_publication_text


async def send_preview(
    *,
    bot: Bot,
    chat_id: int,
    post: SuggestedPost,
    reply_to_message_id: int | None = None,
) -> list[Message]:
    text = compose_publication_text(post)
    return await send_rendered_post(
        bot=bot,
        chat_id=chat_id,
        file_id=post.file_id,
        text=text,
        reply_to_message_id=reply_to_message_id,
    )


async def send_rendered_post(
    *,
    bot: Bot,
    chat_id: int,
    file_id: str | None,
    text: str | None,
    reply_to_message_id: int | None = None,
) -> list[Message]:
    sent_messages: list[Message] = []

    if file_id:
        if text and len(text) <= 1024:
            sent_messages.append(
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=file_id,
                    caption=text,
                    parse_mode=None,
                    reply_to_message_id=reply_to_message_id,
                )
            )
            return sent_messages

        sent_messages.append(
            await bot.send_photo(
                chat_id=chat_id,
                photo=file_id,
                parse_mode=None,
                reply_to_message_id=reply_to_message_id,
            )
        )
        if text:
            sent_messages.append(await bot.send_message(chat_id=chat_id, text=text, parse_mode=None))
        return sent_messages

    if not text:
        raise ValueError("Text-only preview cannot be empty.")

    sent_messages.append(
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=None,
            reply_to_message_id=reply_to_message_id,
        )
    )
    return sent_messages
