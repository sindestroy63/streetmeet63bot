from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    waiting_for_broadcast_content = State()
    waiting_for_broadcast_confirm = State()
    waiting_for_schedule_datetime = State()
