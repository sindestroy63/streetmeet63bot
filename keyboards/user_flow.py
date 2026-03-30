from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

SKIP_BUTTON = "Пропустить"
CANCEL_BUTTON = "❌ Отмена"


class UserSubmissionCallback(CallbackData, prefix="user_submit"):
    action: str


def build_photo_step_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_BUTTON)]],
        resize_keyboard=True,
    )


def build_caption_step_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=SKIP_BUTTON)],
            [KeyboardButton(text=CANCEL_BUTTON)],
        ],
        resize_keyboard=True,
    )


def build_publish_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👤 От моего имени",
                    callback_data=UserSubmissionCallback(action="mode_author").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🙈 Анонимно",
                    callback_data=UserSubmissionCallback(action="mode_anonymous").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=UserSubmissionCallback(action="cancel").pack(),
                )
            ],
        ]
    )


def build_confirmation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Отправить",
                    callback_data=UserSubmissionCallback(action="confirm").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Изменить",
                    callback_data=UserSubmissionCallback(action="restart").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=UserSubmissionCallback(action="cancel").pack(),
                )
            ],
        ]
    )
