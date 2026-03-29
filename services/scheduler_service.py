from __future__ import annotations

import asyncio
import logging

from config import Settings
from database import Database
from services.moderation_service import refresh_moderation_card
from services.publication_service import publish_submission
from utils.datetime_utils import now_in_timezone
from utils.texts import SCHEDULED_POST_PUBLISHED_TEXT


logger = logging.getLogger(__name__)


async def run_scheduler(database: Database, bot, settings: Settings, interval_seconds: int = 25) -> None:
    try:
        while True:
            await _process_due_posts(database=database, bot=bot, settings=settings)
            await asyncio.sleep(interval_seconds)
    except asyncio.CancelledError:
        raise


async def _process_due_posts(*, database: Database, bot, settings: Settings) -> None:
    now_iso = now_in_timezone(settings.timezone).isoformat()
    due_posts = await database.get_due_scheduled_posts(now_iso)

    for post in due_posts:
        try:
            ok, _ = await publish_submission(
                database=database,
                bot=bot,
                settings=settings,
                post=post,
                moderator_id=None,
                source_status="scheduled",
            )
            updated_post = await database.get_post(post.id)
            if updated_post:
                await refresh_moderation_card(bot, settings, updated_post)
            if ok and updated_post:
                await bot.send_message(
                    settings.admin_chat_id,
                    SCHEDULED_POST_PUBLISHED_TEXT.format(post_id=updated_post.id),
                )
        except Exception:
            logger.exception("Failed to process scheduled post %s", post.id)
