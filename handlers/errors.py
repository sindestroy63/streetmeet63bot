from __future__ import annotations

import logging
from contextlib import suppress

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types.error_event import ErrorEvent


async def global_error_handler(event: ErrorEvent) -> bool:
    logging.exception("Unhandled update processing error", exc_info=event.exception)

    if event.update.callback_query:
        with suppress(TelegramBadRequest):
            await event.update.callback_query.answer(
                "Произошла ошибка. Попробуйте ещё раз.",
                show_alert=True,
            )
    elif event.update.message:
        with suppress(TelegramBadRequest, TelegramForbiddenError):
            await event.update.message.answer("Произошла ошибка. Попробуйте ещё раз позже.")

    return True
