from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


ADMIN_BROADCAST_BUTTON = "📢 Рассылка"
ADMIN_USERS_BUTTON = "👥 Пользователи"
ADMIN_STATS_BUTTON = "📊 Статистика"
ADMIN_GIVEAWAY_BUTTON = "🎁 Розыгрыш (админ)"
ADMIN_CLOSE_BUTTON = "❌ Закрыть"
ADMIN_CANCEL_BUTTON = "❌ Отмена"
ADMIN_PANEL_BUTTON = "⚙️ Админка"


class AdminCallback(CallbackData, prefix="admin"):
    action: str


def build_admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADMIN_BROADCAST_BUTTON)],
            [KeyboardButton(text=ADMIN_USERS_BUTTON), KeyboardButton(text=ADMIN_STATS_BUTTON)],
            [KeyboardButton(text=ADMIN_GIVEAWAY_BUTTON)],
            [KeyboardButton(text=ADMIN_CLOSE_BUTTON)],
        ],
        resize_keyboard=True,
    )


def get_admin_menu() -> ReplyKeyboardMarkup:
    return build_admin_menu()


def build_admin_menu_keyboard() -> ReplyKeyboardMarkup:
    return build_admin_menu()


def build_admin_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=ADMIN_CANCEL_BUTTON)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def build_admin_inline_close_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=ADMIN_CLOSE_BUTTON,
                    callback_data=AdminCallback(action="close_panel").pack(),
                )
            ]
        ]
    )


def get_admin_cancel_keyboard() -> ReplyKeyboardMarkup:
    return build_admin_cancel_keyboard()
