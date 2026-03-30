from __future__ import annotations

import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.types import User

from config import Settings
from database import BotUser, Database
from utils.subscription import check_subscription_result


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SubscriptionStatus:
    is_subscribed: bool
    can_check: bool
    error_text: str | None = None

    @property
    def subscribed(self) -> bool:
        return self.is_subscribed

    @property
    def is_available(self) -> bool:
        return self.can_check

    @property
    def message(self) -> str | None:
        return self.error_text


async def register_user(
    database: Database,
    settings: Settings,
    telegram_user: User,
) -> tuple[BotUser, bool]:
    return await database.upsert_user(
        telegram_id=telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
        is_admin=settings.is_admin(telegram_user.id),
    )


async def sync_subscription_status(
    bot: Bot,
    database: Database,
    settings: Settings,
    user_id: int,
) -> SubscriptionStatus:
    result = await check_subscription_result(
        bot=bot,
        user_id=user_id,
        settings=settings,
    )

    logger.info(
        "Subscription check user_id=%s channel=%s subscribed=%s available=%s error=%s",
        user_id,
        settings.channel_id,
        result.is_subscribed,
        result.is_available,
        result.error_text,
    )

    if result.is_available:
        await database.update_user_subscription(user_id, result.is_subscribed)

    return SubscriptionStatus(
        is_subscribed=result.is_subscribed,
        can_check=result.is_available,
        error_text=result.error_text,
    )


async def notify_about_new_user(
    bot: Bot,
    database: Database,
    settings: Settings,
    user: BotUser,
) -> None:
    total_users = await database.get_total_users_count()
    user_label = f"@{user.username}" if user.username else f"ID {user.telegram_id}"
    text = (
        f"<b>👤 Новый пользователь: {user_label}</b>\n\n"
        f"<b>Всего пользователей:</b> {total_users}"
    )

    try:
        await bot.send_message(
            chat_id=settings.admin_chat_id,
            text=text,
        )
    except Exception as error:
        logger.warning("Failed to notify admin about new user %s: %s", user.telegram_id, error)
