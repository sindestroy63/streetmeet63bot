from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class SubscriptionCallback(CallbackData, prefix="sub"):
    action: str


def build_subscription_keyboard(channel_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Подписаться", url=channel_url),
            ],
            [
                InlineKeyboardButton(
                    text="✅ Проверить подписку",
                    callback_data=SubscriptionCallback(action="check").pack(),
                )
            ],
        ]
    )


def get_subscription_keyboard(channel_url: str) -> InlineKeyboardMarkup:
    return build_subscription_keyboard(channel_url)
