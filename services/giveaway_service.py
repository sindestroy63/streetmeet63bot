from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime

from aiogram import Bot
from aiogram.enums import ChatMemberStatus


logger = logging.getLogger(__name__)

ALLOWED_SUBSCRIPTION_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
}


@dataclass(slots=True)
class GiveawayCheckResult:
    subscribed_channel_1: bool
    subscribed_channel_2: bool

    @property
    def is_valid(self) -> bool:
        return self.subscribed_channel_1 and self.subscribed_channel_2


def _extract_channel_ref(url: str) -> str:
    value = (url or "").strip()
    if "t.me/" in value:
        value = value.split("t.me/", maxsplit=1)[1]
    value = value.strip().strip("/")
    return value if value.startswith("@") else f"@{value}"


async def _check_single_subscription(bot: Bot, user_id: int, channel_url: str) -> bool:
    channel_ref = _extract_channel_ref(channel_url)
    try:
        member = await bot.get_chat_member(chat_id=channel_ref, user_id=user_id)
    except Exception as error:
        logger.warning("Giveaway subscription check failed for %s in %s: %s", user_id, channel_ref, error)
        return False
    return member.status in ALLOWED_SUBSCRIPTION_STATUSES


async def check_giveaway_subscriptions(bot: Bot, settings, user_id: int) -> GiveawayCheckResult:
    channel_1 = await _check_single_subscription(bot, user_id, settings.giveaway_channel_1_url)
    channel_2 = await _check_single_subscription(bot, user_id, settings.giveaway_channel_2_url)
    return GiveawayCheckResult(
        subscribed_channel_1=channel_1,
        subscribed_channel_2=channel_2,
    )


async def join_giveaway(bot: Bot, database, settings, telegram_user) -> tuple[bool, bool]:
    result = await check_giveaway_subscriptions(bot, settings, telegram_user.id)
    if not result.is_valid:
        return False, False

    _, created = await database.upsert_giveaway_participant(
        telegram_id=telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
    )
    return True, created


async def get_giveaway_overview(database, settings) -> dict:
    stats = await database.get_giveaway_stats()
    participants = await database.get_all_giveaway_participants()
    return {
        "stats": stats,
        "participants": participants,
        "draw_at": settings.giveaway_draw_at,
        "winners_count": settings.giveaway_winners_count,
    }


def _winner_label(participant) -> str:
    if participant.username:
        return f"@{participant.username}"
    if participant.first_name:
        return f"{participant.first_name} / ID {participant.telegram_id}"
    return f"ID {participant.telegram_id}"


async def draw_giveaway_winners(bot: Bot, database, settings) -> list:
    if await database.is_giveaway_draw_completed():
        return await database.get_giveaway_winners()

    participants = await database.get_all_giveaway_participants()
    valid_participants = []

    for participant in participants:
        result = await check_giveaway_subscriptions(bot, settings, participant.telegram_id)
        if result.is_valid:
            valid_participants.append(participant)

    if not valid_participants:
        await database.mark_giveaway_draw_completed()
        return []

    winners_count = min(settings.giveaway_winners_count, len(valid_participants))
    winners = random.sample(valid_participants, winners_count)
    winner_ids = [winner.telegram_id for winner in winners]
    await database.set_giveaway_winners(winner_ids)
    await database.mark_giveaway_draw_completed()
    return winners


async def notify_admin_about_giveaway_results(bot: Bot, settings, winners: list) -> None:
    if winners:
        winners_lines = "\n".join(
            f"{index}. {_winner_label(winner)}" for index, winner in enumerate(winners, start=1)
        )
    else:
        winners_lines = "Победителей нет"

    text = (
        "<b>🎉 Розыгрыш завершён</b>\n\n"
        "<b>Победители:</b>\n\n"
        f"{winners_lines}"
    )
    await bot.send_message(chat_id=settings.admin_chat_id, text=text)


async def run_giveaway_scheduler(database, bot: Bot, settings, interval_seconds: int = 30) -> None:
    while True:
        try:
            if not await database.is_giveaway_draw_completed():
                now = datetime.now(settings.timezone)
                if now >= settings.giveaway_draw_at:
                    winners = await draw_giveaway_winners(bot, database, settings)
                    await notify_admin_about_giveaway_results(bot, settings, winners)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.exception("Giveaway scheduler failed: %s", error)

        await asyncio.sleep(interval_seconds)
