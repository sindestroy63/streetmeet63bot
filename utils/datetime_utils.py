from __future__ import annotations

from datetime import datetime, timedelta


def now_in_timezone(tzinfo) -> datetime:
    return datetime.now(tzinfo)


def format_datetime_display(value: str | None, tzinfo) -> str:
    if not value:
        return "—"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=tzinfo)
    localized = parsed.astimezone(tzinfo)
    return localized.strftime("%d.%m.%Y %H:%M")


def parse_manual_datetime(raw_value: str, tzinfo) -> datetime:
    parsed = datetime.strptime(raw_value.strip(), "%d.%m.%Y %H:%M")
    return parsed.replace(tzinfo=tzinfo)


def is_future_datetime(target: datetime, tzinfo) -> bool:
    return target > now_in_timezone(tzinfo)


def quick_schedule_datetime(kind: str, tzinfo) -> datetime:
    now = now_in_timezone(tzinfo)

    if kind == "plus_30":
        return now + timedelta(minutes=30)
    if kind == "plus_60":
        return now + timedelta(hours=1)
    if kind == "today_18":
        return _today_or_tomorrow(now, tzinfo, 18, 0)
    if kind == "today_21":
        return _today_or_tomorrow(now, tzinfo, 21, 0)
    if kind == "tomorrow_12":
        tomorrow = now.date() + timedelta(days=1)
        return datetime(tomorrow.year, tomorrow.month, tomorrow.day, 12, 0, tzinfo=tzinfo)
    if kind == "tomorrow_18":
        tomorrow = now.date() + timedelta(days=1)
        return datetime(tomorrow.year, tomorrow.month, tomorrow.day, 18, 0, tzinfo=tzinfo)

    raise ValueError(f"Unknown quick schedule kind: {kind}")


def _today_or_tomorrow(now: datetime, tzinfo, hour: int, minute: int) -> datetime:
    candidate = datetime(now.year, now.month, now.day, hour, minute, tzinfo=tzinfo)
    if candidate <= now:
        candidate = candidate + timedelta(days=1)
    return candidate
