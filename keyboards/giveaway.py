from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class GiveawayCallback(CallbackData, prefix="giveaway"):
    action: str


class LegacyGiveawayAdminCallback(CallbackData, prefix="giveaway_admin"):
    action: str


def build_giveaway_keyboard(channel_1_url: str, channel_2_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 STREETMEET63", url=channel_1_url)],
            [InlineKeyboardButton(text="📢 TOP4IKA", url=channel_2_url)],
            [InlineKeyboardButton(text="✅ Участвовать", callback_data=GiveawayCallback(action="join_contest").pack())],
            [InlineKeyboardButton(text="🔄 Проверить", callback_data=GiveawayCallback(action="check_subscriptions").pack())],
        ]
    )


def build_giveaway_admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Участники", callback_data=GiveawayCallback(action="view_participants").pack())],
            [InlineKeyboardButton(text="🎲 Выбрать победителей", callback_data=GiveawayCallback(action="draw_winners").pack())],
            [InlineKeyboardButton(text="📊 Статистика", callback_data=GiveawayCallback(action="view_stats").pack())],
            [InlineKeyboardButton(text="⬅ К обзору", callback_data=GiveawayCallback(action="view_overview").pack())],
        ]
    )
