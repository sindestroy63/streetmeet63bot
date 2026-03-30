from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from config import Settings


SUBSCRIBED_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
}


@dataclass(slots=True)
class SubscriptionCheckResult:
    is_subscribed: bool
    is_available: bool
    error_text: str | None = None

    @property
    def can_check(self) -> bool:
        return self.is_available

    @property
    def subscribed(self) -> bool:
        return self.is_subscribed

    @property
    def message(self) -> str | None:
        return self.error_text


def _resolve_chat_id(
    settings: Settings | None = None,
    channel_id: int | str | None = None,
) -> int | str:
    if channel_id is not None:
        return channel_id
    if settings is not None:
        return settings.channel_id
    raise ValueError("Channel reference is missing")


def _extract_username_from_url(url: str | None) -> str | None:
    value = (url or "").strip()
    if not value:
        return None

    if "t.me/" in value:
        value = value.split("t.me/", maxsplit=1)[1]

    value = value.strip().strip("/")
    if not value:
        return None

    if value.startswith("+"):
        return None

    return value if value.startswith("@") else f"@{value}"


def _candidate_chat_ids(
    settings: Settings | None = None,
    channel_id: int | str | None = None,
) -> list[int | str]:
    candidates: list[int | str] = []

    if channel_id is not None:
        candidates.append(channel_id)
    elif settings is not None:
        candidates.append(settings.channel_id)
        username = _extract_username_from_url(settings.channel_url)
        if username is not None:
            candidates.append(username)

    unique_candidates: list[int | str] = []
    seen: set[str] = set()

    for item in candidates:
        key = str(item)
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(item)

    return unique_candidates


def get_subscription_chat_id(
    settings: Settings | None = None,
    channel_id: int | str | None = None,
) -> int | str:
    return _resolve_chat_id(settings=settings, channel_id=channel_id)


async def check_subscription_result(
    bot: Bot,
    user_id: int,
    settings: Settings | None = None,
    channel_id: int | str | None = None,
) -> SubscriptionCheckResult:
    chat_ids = _candidate_chat_ids(settings=settings, channel_id=channel_id)
    if not chat_ids:
        return SubscriptionCheckResult(
            is_subscribed=False,
            is_available=False,
            error_text=(
                "Не удалось проверить подписку.\n\n"
                "Не задан канал для проверки."
            ),
        )

    last_error_text: str | None = None

    for chat_id in chat_ids:
        if isinstance(chat_id, int) and chat_id > 0:
            last_error_text = (
                "CHANNEL_ID указан неверно.\n\n"
                "Используй <code>-100...</code>, <code>@username</code> "
                "или ссылку <code>https://t.me/...</code>."
            )
            continue

        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        except TelegramForbiddenError:
            return SubscriptionCheckResult(
                is_subscribed=False,
                is_available=False,
                error_text=(
                    "Бот не может проверить подписку.\n\n"
                    "Добавь бота в канал администратором."
                ),
            )
        except TelegramBadRequest as error:
            error_text = str(error).lower()

            if "chat not found" in error_text:
                last_error_text = (
                    "Канал не найден.\n\n"
                    "Проверь <code>CHANNEL_ID</code> или публичную ссылку канала."
                )
                continue

            if "user not found" in error_text:
                return SubscriptionCheckResult(
                    is_subscribed=False,
                    is_available=True,
                    error_text="Подписка пока не найдена. Подпишись на канал и попробуй ещё раз.",
                )

            return SubscriptionCheckResult(
                is_subscribed=False,
                is_available=False,
                error_text=f"Не удалось проверить подписку.\n\n<i>{error}</i>",
            )
        except Exception as error:
            return SubscriptionCheckResult(
                is_subscribed=False,
                is_available=False,
                error_text=(
                    "Не удалось проверить подписку.\n\n"
                    f"<i>{type(error).__name__}: {error}</i>"
                ),
            )

        return SubscriptionCheckResult(
            is_subscribed=member.status in SUBSCRIBED_STATUSES,
            is_available=True,
        )

    return SubscriptionCheckResult(
        is_subscribed=False,
        is_available=False,
        error_text=last_error_text
        or "Не удалось проверить подписку.",
    )


async def is_user_subscribed(
    bot: Bot,
    settings: Settings | None = None,
    user_id: int | None = None,
    channel_id: int | str | None = None,
) -> bool:
    if user_id is None:
        raise ValueError("user_id is required")
    result = await check_subscription_result(
        bot=bot,
        user_id=user_id,
        settings=settings,
        channel_id=channel_id,
    )
    return result.is_subscribed


async def check_subscription(
    bot: Bot,
    settings: Settings | None = None,
    user_id: int | None = None,
    channel_id: int | str | None = None,
) -> bool:
    if user_id is None:
        raise ValueError("user_id is required")
    result = await check_subscription_result(
        bot=bot,
        user_id=user_id,
        settings=settings,
        channel_id=channel_id,
    )
    return result.is_subscribed


async def check_user_subscription(
    bot: Bot,
    settings: Settings | None = None,
    user_id: int | None = None,
    channel_id: int | str | None = None,
) -> tuple[bool, str | None]:
    if user_id is None:
        raise ValueError("user_id is required")
    result = await check_subscription_result(
        bot=bot,
        user_id=user_id,
        settings=settings,
        channel_id=channel_id,
    )
    return result.is_subscribed, result.error_text


async def get_subscription_status(
    bot: Bot,
    settings: Settings | None = None,
    user_id: int | None = None,
    channel_id: int | str | None = None,
) -> tuple[bool, bool, str | None]:
    if user_id is None:
        raise ValueError("user_id is required")
    result = await check_subscription_result(
        bot=bot,
        user_id=user_id,
        settings=settings,
        channel_id=channel_id,
    )
    return result.is_subscribed, result.is_available, result.error_text


async def check_channel_subscription(
    bot: Bot,
    settings: Settings | None = None,
    user_id: int | None = None,
    channel_id: int | str | None = None,
) -> SubscriptionCheckResult:
    if user_id is None:
        raise ValueError("user_id is required")
    return await check_subscription_result(
        bot=bot,
        user_id=user_id,
        settings=settings,
        channel_id=channel_id,
    )
