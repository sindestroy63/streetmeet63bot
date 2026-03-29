from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError


ALLOWED_SUBSCRIPTION_STATUSES = {"member", "administrator", "creator"}


@dataclass(slots=True)
class SubscriptionCheckResult:
    is_subscribed: bool
    can_check: bool


async def check_channel_subscription(
    *,
    bot: Bot,
    channel_id: int,
    user_id: int,
) -> SubscriptionCheckResult:
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
    except TelegramAPIError:
        return SubscriptionCheckResult(is_subscribed=False, can_check=False)

    status = getattr(member, "status", "")
    return SubscriptionCheckResult(
        is_subscribed=status in ALLOWED_SUBSCRIPTION_STATUSES,
        can_check=True,
    )
