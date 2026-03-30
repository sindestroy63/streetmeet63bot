from __future__ import annotations

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, Message


MAX_CAPTION_LENGTH = 1024
LEGACY_LINK_BLOCK_MARKERS = (
    "━━━━━━━━━━━━━━━━",
    "📩 Как предложить пост?",
    "🤖 через бота",
    "💬 общаемся в чате",
)


def _strip_legacy_links_block(text: str | None) -> str | None:
    if not text:
        return text

    cleaned = text

    if "━━━━━━━━━━━━━━━━" in cleaned:
        cleaned = cleaned.split("━━━━━━━━━━━━━━━━", maxsplit=1)[0].rstrip()

    for marker in LEGACY_LINK_BLOCK_MARKERS[1:]:
        cleaned = cleaned.replace(marker, "")

    cleaned = cleaned.strip()
    return cleaned or None


async def send_preview(
    bot: Bot,
    chat_id: int,
    file_id: str | None,
    text: str | None,
    reply_to_message_id: int | None = None,
) -> list[int]:
    return await send_rendered_post(
        bot=bot,
        chat_id=chat_id,
        file_id=file_id,
        text=text,
        reply_to_message_id=reply_to_message_id,
        reply_markup=None,
    )


async def send_rendered_post(
    bot: Bot,
    chat_id: int,
    file_id: str | None,
    text: str | None,
    reply_to_message_id: int | None = None,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> list[int]:
    text = _strip_legacy_links_block(text)
    sent_messages: list[Message] = []

    if file_id and text and len(text) <= MAX_CAPTION_LENGTH:
        sent_messages.append(
            await bot.send_photo(
                chat_id=chat_id,
                photo=file_id,
                caption=text,
                reply_markup=reply_markup,
                parse_mode=None,
                reply_to_message_id=reply_to_message_id,
            )
        )
        return [message.message_id for message in sent_messages]

    if file_id:
        sent_messages.append(
            await bot.send_photo(
                chat_id=chat_id,
                photo=file_id,
                parse_mode=None,
                reply_to_message_id=reply_to_message_id,
            )
        )

    if text:
        sent_messages.append(
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=None,
                reply_to_message_id=reply_to_message_id if not sent_messages else None,
            )
        )
    elif file_id and reply_markup is not None:
        last_message = sent_messages[-1]
        await bot.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=last_message.message_id,
            reply_markup=reply_markup,
        )

    return [message.message_id for message in sent_messages]
