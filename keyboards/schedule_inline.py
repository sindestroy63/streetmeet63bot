from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class ScheduleCallback(CallbackData, prefix="scheduling"):
    action: str
    post_id: int


class LegacyScheduleCallback(CallbackData, prefix="schedule"):
    action: str
    post_id: int


def build_schedule_keyboard(post_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="+30 мин",
                    callback_data=ScheduleCallback(action="set_plus_30m", post_id=post_id).pack(),
                ),
                InlineKeyboardButton(
                    text="+1 час",
                    callback_data=ScheduleCallback(action="set_plus_1h", post_id=post_id).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Сегодня 18:00",
                    callback_data=ScheduleCallback(action="set_today_18", post_id=post_id).pack(),
                ),
                InlineKeyboardButton(
                    text="Сегодня 21:00",
                    callback_data=ScheduleCallback(action="set_today_21", post_id=post_id).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Завтра 12:00",
                    callback_data=ScheduleCallback(action="set_tomorrow_12", post_id=post_id).pack(),
                ),
                InlineKeyboardButton(
                    text="Завтра 18:00",
                    callback_data=ScheduleCallback(action="set_tomorrow_18", post_id=post_id).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📝 Ввести вручную",
                    callback_data=ScheduleCallback(action="open_manual_input", post_id=post_id).pack(),
                ),
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=ScheduleCallback(action="cancel_flow", post_id=post_id).pack(),
                ),
            ],
        ]
    )
