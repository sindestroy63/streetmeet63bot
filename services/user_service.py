from __future__ import annotations

from datetime import datetime, timezone
from html import escape

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from config import Settings
from database import BotUser, Database
from utils.subscription import SubscriptionCheckResult, check_channel_subscription
from utils.texts import NEW_USER_NOTIFICATION_TEMPLATE


async def register_user(
    *,
    database: Database,
    settings: Settings,
    telegram_user,
) -> tuple[BotUser, bool]:
    return await database.upsert_user(
        telegram_id=telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
        is_admin=settings.is_admin(telegram_user.id),
        current_time=datetime.now(timezone.utc).isoformat(),
    )


async def sync_subscription_status(
    *,
    database: Database,
    bot: Bot,
    settings: Settings,
    user_id: int,
) -> SubscriptionCheckResult:
    result = await check_channel_subscription(
        bot=bot,
        channel_id=settings.channel_id,
        user_id=user_id,
    )
    if result.can_check:
        await database.update_user_subscription(user_id, result.is_subscribed)
    return result


async def notify_about_new_user(
    *,
    bot: Bot,
    settings: Settings,
    user: BotUser,
) -> None:
    username = f"@{escape(user.username)}" if user.username else "—"
    first_name = escape(user.first_name or "—")
    created_at = datetime.fromisoformat(user.created_at).strftime("%d.%m.%Y %H:%M")
    text = NEW_USER_NOTIFICATION_TEMPLATE.format(
        first_name=first_name,
        username=username,
        telegram_id=user.telegram_id,
        created_at=created_at,
    )
    try:
        await bot.send_message(settings.admin_chat_id, text)
    except TelegramBadRequest:
        return
