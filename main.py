from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import load_settings
from database import Database
from handlers.admin_broadcast import get_router as get_admin_broadcast_router
from handlers.admin_editing import get_router as get_admin_editing_router
from handlers.admin_moderation import get_router as get_admin_moderation_router
from handlers.admin_panel import get_router as get_admin_panel_router
from handlers.admin_scheduling import get_router as get_admin_scheduling_router
from handlers.admin_stats import get_router as get_admin_stats_router
from handlers.errors import global_error_handler
from handlers.user_start import get_router as get_user_start_router
from handlers.user_submission import get_router as get_user_submission_router
from services.scheduler_service import run_scheduler


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def main() -> None:
    setup_logging()
    settings = load_settings()
    database = Database(settings.database_path)
    await database.init()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(get_user_start_router(database, settings))
    dispatcher.include_router(get_admin_panel_router(settings))
    dispatcher.include_router(get_admin_broadcast_router(database, settings))
    dispatcher.include_router(get_admin_stats_router(database, settings))
    dispatcher.include_router(get_user_submission_router(database, settings))
    dispatcher.include_router(get_admin_scheduling_router(database, settings))
    dispatcher.include_router(get_admin_moderation_router(database, settings))
    dispatcher.include_router(get_admin_editing_router(database, settings))
    dispatcher.errors.register(global_error_handler)

    await bot.delete_webhook(drop_pending_updates=False)
    scheduler_task = asyncio.create_task(run_scheduler(database, bot, settings))

    try:
        await dispatcher.start_polling(bot)
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
        await database.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
