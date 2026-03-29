from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from database import Database


@dataclass(slots=True)
class BroadcastResult:
    success: int
    failed: int


async def broadcast_to_users(
    *,
    database: Database,
    bot: Bot,
    text: str | None,
    photo_file_id: str | None,
) -> BroadcastResult:
    success = 0
    failed = 0

    for user in await database.get_broadcast_users():
        try:
            if photo_file_id:
                await bot.send_photo(
                    chat_id=user.telegram_id,
                    photo=photo_file_id,
                    caption=text,
                )
            elif text:
                await bot.send_message(chat_id=user.telegram_id, text=text)
            else:
                raise ValueError("Broadcast content is empty.")
            success += 1
        except TelegramForbiddenError:
            failed += 1
            await database.mark_user_blocked(user.telegram_id, True)
        except TelegramBadRequest as exc:
            failed += 1
            error_text = str(exc).lower()
            if "blocked" in error_text or "chat not found" in error_text or "user is deactivated" in error_text:
                await database.mark_user_blocked(user.telegram_id, True)
        except Exception:
            failed += 1

    return BroadcastResult(success=success, failed=failed)
