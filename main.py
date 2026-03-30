from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from config import load_settings
from database import Database
from handlers.admin_broadcast import get_router as get_admin_broadcast_router
from handlers.admin_giveaway import get_router as get_admin_giveaway_router
from handlers.admin_moderation import get_router as get_admin_moderation_router
from handlers.admin_panel import get_router as get_admin_panel_router
from handlers.admin_scheduling import get_router as get_admin_scheduling_router
from handlers.admin_stats import get_router as get_admin_stats_router
from handlers.giveaway import get_router as get_giveaway_router
from handlers.user_start import get_router as get_user_start_router
from handlers.user_submission import get_router as get_user_submission_router
from services.giveaway_service import run_giveaway_scheduler
from services.scheduler_service import run_scheduler


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    settings = load_settings()
    database = Database(settings.database_path)
    await database.init()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dispatcher = Dispatcher()

    dispatcher.include_router(get_user_start_router(database, settings))
    dispatcher.include_router(get_giveaway_router(database, settings))
    dispatcher.include_router(get_admin_panel_router(database, settings))
    dispatcher.include_router(get_admin_broadcast_router(database, settings))
    dispatcher.include_router(get_admin_stats_router(database, settings))
    dispatcher.include_router(get_admin_giveaway_router(database, settings))
    dispatcher.include_router(get_user_submission_router(database, settings))
    dispatcher.include_router(get_admin_scheduling_router(database, settings))
    dispatcher.include_router(get_admin_moderation_router(database, settings))

    scheduler_task = asyncio.create_task(run_scheduler(database, bot, settings))
    giveaway_task = asyncio.create_task(run_giveaway_scheduler(database, bot, settings))

    try:
        await dispatcher.start_polling(bot)
    finally:
        scheduler_task.cancel()
        giveaway_task.cancel()
        await asyncio.gather(scheduler_task, giveaway_task, return_exceptions=True)
        await database.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
