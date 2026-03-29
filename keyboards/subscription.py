from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class SubscriptionCallback(CallbackData, prefix="sub"):
    action: str


def build_subscription_keyboard(channel_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Подписаться", url=channel_url)
    builder.button(
        text="✅ Проверить подписку",
        callback_data=SubscriptionCallback(action="check").pack(),
    )
    builder.adjust(1, 1)
    return builder.as_markup()
