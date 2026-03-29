from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


SKIP_BUTTON = "Пропустить"
CANCEL_BUTTON = "❌ Отмена"


class UserFlowCallback(CallbackData, prefix="uf"):
    action: str


def build_photo_step_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_BUTTON)]],
        resize_keyboard=True,
        selective=True,
    )


def build_caption_step_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=SKIP_BUTTON)],
            [KeyboardButton(text=CANCEL_BUTTON)],
        ],
        resize_keyboard=True,
        selective=True,
    )


def build_publish_mode_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👤 От моего имени", callback_data=UserFlowCallback(action="mode_author").pack())
    builder.button(text="🙈 Анонимно", callback_data=UserFlowCallback(action="mode_anonymous").pack())
    builder.button(text="❌ Отмена", callback_data=UserFlowCallback(action="cancel").pack())
    builder.adjust(1, 1, 1)
    return builder.as_markup()


def build_summary_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить", callback_data=UserFlowCallback(action="confirm").pack())
    builder.button(text="✏️ Изменить", callback_data=UserFlowCallback(action="edit").pack())
    builder.button(text="❌ Отмена", callback_data=UserFlowCallback(action="cancel").pack())
    builder.adjust(1, 2)
    return builder.as_markup()
