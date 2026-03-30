from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class GiveawayCallback(CallbackData, prefix="giveaway"):
    action: str


class GiveawayAdminCallback(CallbackData, prefix="giveaway_admin"):
    action: str


def build_giveaway_keyboard(channel_1_url: str, channel_2_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 STREETMEET63", url=channel_1_url)],
            [InlineKeyboardButton(text="📢 TOP4IKA", url=channel_2_url)],
            [InlineKeyboardButton(text="✅ Участвовать", callback_data=GiveawayCallback(action="join").pack())],
            [InlineKeyboardButton(text="🔄 Проверить", callback_data=GiveawayCallback(action="check").pack())],
        ]
    )


def build_giveaway_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Участники", callback_data=GiveawayAdminCallback(action="participants").pack())],
            [InlineKeyboardButton(text="🎲 Выбрать победителей", callback_data=GiveawayAdminCallback(action="draw").pack())],
            [InlineKeyboardButton(text="📊 Статистика", callback_data=GiveawayAdminCallback(action="stats").pack())],
        ]
    )
