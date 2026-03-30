from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class ModerationCallback(CallbackData, prefix="mod"):
    action: str
    post_id: int


ACTIVE_MODERATION_STATUSES = {"pending", "scheduled"}


def build_moderation_main_keyboard(post) -> InlineKeyboardMarkup:
    if getattr(post, "status", "") not in ACTIVE_MODERATION_STATUSES:
        return InlineKeyboardMarkup(inline_keyboard=[])

    post_id = post.id
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Опубликовать",
                    callback_data=ModerationCallback(action="publish", post_id=post_id).pack(),
                ),
                InlineKeyboardButton(
                    text="⏰ Запланировать",
                    callback_data=ModerationCallback(action="schedule", post_id=post_id).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=ModerationCallback(action="reject", post_id=post_id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать",
                    callback_data=ModerationCallback(action="edit_menu", post_id=post_id).pack(),
                )
            ],
        ]
    )
