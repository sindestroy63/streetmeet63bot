from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.moderation_main import ACTIVE_MODERATION_STATUSES, ModerationCallback


def _author_base_label(post) -> str:
    if getattr(post, "username", None):
        return f"@{post.username}"
    if getattr(post, "first_name", None):
        return post.first_name
    return f"ID {post.user_id}"


def build_moderation_author_keyboard(post) -> InlineKeyboardMarkup | None:
    if getattr(post, "status", None) not in ACTIVE_MODERATION_STATUSES:
        return None

    base_label = _author_base_label(post)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=base_label,
                    callback_data=ModerationCallback(action="sign_user", post_id=post.id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"от {base_label}",
                    callback_data=ModerationCallback(action="sign_from", post_id=post.id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="ID автора",
                    callback_data=ModerationCallback(action="sign_id", post_id=post.id).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=ModerationCallback(action="menu_edit", post_id=post.id).pack(),
                )
            ],
        ]
    )
