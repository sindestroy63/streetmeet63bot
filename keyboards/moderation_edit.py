from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.moderation_main import ModerationCallback


def build_moderation_edit_keyboard(post) -> InlineKeyboardMarkup:
    post_id = post.id
    anonymous_text = "🙈 Анонимно: вкл" if getattr(post, "anonymous", False) else "🙈 Анонимно: выкл"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Текст",
                    callback_data=ModerationCallback(action="edit_text", post_id=post_id).pack(),
                ),
                InlineKeyboardButton(
                    text="🏷 Подпись",
                    callback_data=ModerationCallback(action="edit_signature", post_id=post_id).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=anonymous_text,
                    callback_data=ModerationCallback(action="toggle_anonymous", post_id=post_id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Убрать подпись",
                    callback_data=ModerationCallback(action="clear_signature", post_id=post_id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=ModerationCallback(action="back_main", post_id=post_id).pack(),
                )
            ],
        ]
    )
