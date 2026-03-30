from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup

from utils.formatters import compose_publication_text


CAPTION_LIMIT = 1024


def _normalize_media_type(media_type: str | None, file_id: str | None) -> str:
    normalized = (media_type or "").strip().lower()
    if normalized in {"photo", "video"}:
        return normalized
    if file_id:
        return "photo"
    return ""


def _split_caption(text: str) -> tuple[str | None, str | None]:
    prepared = (text or "").strip()
    if not prepared:
        return None, None
    if len(prepared) <= CAPTION_LIMIT:
        return prepared, None
    return None, prepared


async def send_media_content(
    bot,
    chat_id: int | str,
    *,
    file_id: str = "",
    media_type: str = "",
    text: str = "",
    reply_markup: InlineKeyboardMarkup | None = None,
):
    normalized_type = _normalize_media_type(media_type, file_id)

    if normalized_type == "video" and file_id:
        caption, trailing_text = _split_caption(text)
        message = await bot.send_video(
            chat_id=chat_id,
            video=file_id,
            caption=caption,
            reply_markup=reply_markup,
        )
        if trailing_text:
            await bot.send_message(chat_id=chat_id, text=trailing_text)
        return message

    if normalized_type == "photo" and file_id:
        caption, trailing_text = _split_caption(text)
        message = await bot.send_photo(
            chat_id=chat_id,
            photo=file_id,
            caption=caption,
            reply_markup=reply_markup,
        )
        if trailing_text:
            await bot.send_message(chat_id=chat_id, text=trailing_text)
        return message

    return await bot.send_message(chat_id=chat_id, text=(text or " ").strip() or " ", reply_markup=reply_markup)


async def send_rendered_post(bot, chat_id: int | str, post, reply_markup: InlineKeyboardMarkup | None = None):
    return await send_media_content(
        bot,
        chat_id,
        file_id=getattr(post, "file_id", "") or "",
        media_type=getattr(post, "media_type", "") or "",
        text=compose_publication_text(post),
        reply_markup=reply_markup,
    )


async def send_preview(bot, chat_id: int, post, reply_markup: InlineKeyboardMarkup | None = None):
    return await send_rendered_post(bot, chat_id, post, reply_markup=reply_markup)
