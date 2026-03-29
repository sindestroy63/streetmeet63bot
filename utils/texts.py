from __future__ import annotations

from html import escape


START_TEXT = (
    "<b>STREETMEET63 — предложка 🚗</b>\n\n"
    "Отправь:\n"
    "• фото\n"
    "• подпись\n"
    "• выбери формат публикации\n\n"
    "<i>После проверки пост опубликуют или отклонят</i>"
)

HOW_IT_WORKS_TEXT = (
    "<b>Как это работает 👇</b>\n\n"
    "1. Отправь фото\n"
    "2. Добавь подпись или пропусти\n"
    "3. Выбери формат публикации\n\n"
    "<i>После этого мы проверим пост и решим, публиковать его или нет</i>"
)

SUBSCRIPTION_REQUIRED_TEXT = (
    "<b>Доступ к боту только для подписчиков 📢</b>\n\n"
    "Подпишись на канал и нажми <b>«Проверить подписку»</b>"
)

SUBSCRIPTION_NOT_FOUND_ALERT = "Подписка пока не найдена."

SUBSCRIPTION_CHECK_ERROR_TEXT = (
    "<b>Не удалось проверить подписку</b>\n\n"
    "<i>Проверь, что бот добавлен в канал и может видеть участников.</i>"
)

SUBSCRIPTION_SUCCESS_TEXT = (
    "<b>Подписка подтверждена ✅</b>\n\n"
    "<i>Теперь можно пользоваться ботом</i>"
)

SEND_POST_TEXT = (
    "<b>Шаг 1 из 3 — фото</b>\n\n"
    "Отправь фото для поста 👇"
)

SEND_PHOTO_ONLY_TEXT = (
    "<b>Нужна фотография</b>\n\n"
    "Отправь именно фото для поста\n"
    "или нажми <b>«Отмена»</b>."
)

STEP_CAPTION_TEXT = (
    "<b>Шаг 2 из 3 — подпись</b>\n\n"
    "Отправь подпись к посту\n"
    "или нажми <b>«Пропустить»</b>"
)

STEP_CAPTION_INVALID_TEXT = (
    "<b>Нужен текст</b>\n\n"
    "Отправь подпись сообщением\n"
    "или нажми <b>«Пропустить»</b>."
)

STEP_MODE_TEXT = (
    "<b>Шаг 3 из 3 — формат публикации</b>\n\n"
    "Выбери, как опубликовать пост 👇"
)

MODE_CHOOSE_ONLY_TEXT = (
    "<b>Выбери формат кнопками ниже</b>\n\n"
    "Используй один из вариантов публикации 👇"
)

SUCCESS_TEXT = (
    "<b>✅ Предложка отправлена</b>\n\n"
    "<i>Мы передали её на модерацию</i>"
)

CANCEL_TEXT = "❌ Отправка отменена"

FLOW_NOT_STARTED_TEXT = (
    "Чтобы отправить предложку,\n"
    "нажми <b>«📸 Отправить пост»</b>."
)

ADMIN_PANEL_TEXT = (
    "<b>⚙️ Админ-панель</b>\n\n"
    "Выбери действие ниже 👇"
)

MAIN_MENU_TEXT = (
    "<b>Главное меню</b>\n\n"
    "Выбери действие ниже 👇"
)

BROADCAST_START_TEXT = (
    "<b>Рассылка</b>\n\n"
    "Отправь текст, который нужно разослать всем пользователям.\n"
    "<i>Можно использовать HTML formatting.</i>"
)

BROADCAST_INVALID_TEXT = (
    "<b>Нужен текст или фото</b>\n\n"
    "Отправь сообщение для рассылки\n"
    "или нажми <b>«Отмена»</b>."
)

BROADCAST_SUCCESS_TEMPLATE = (
    "<b>✅ Рассылка завершена</b>\n\n"
    "<b>Успешно:</b> {success}\n"
    "<b>Ошибок:</b> {failed}"
)

USERS_STATS_TEXT = (
    "<b>Пользователи бота</b>\n\n"
    "<b>Всего:</b> {total}\n"
    "<b>Активных:</b> {active}\n"
    "<b>Заблокировали бота:</b> {blocked}"
)

BOT_STATS_TEXT = (
    "<b>📊 Статистика бота</b>\n\n"
    "<b>Пользователи:</b> {users_total}\n"
    "<b>Новых сегодня:</b> {users_today}\n\n"
    "<b>Всего предложек:</b> {submissions_total}\n"
    "<b>За сегодня:</b> {submissions_today}\n"
    "<b>На модерации:</b> {pending}\n"
    "<b>Опубликовано:</b> {published}\n"
    "<b>Отклонено:</b> {rejected}"
)

NEW_USER_NOTIFICATION_TEMPLATE = (
    "<b>👤 Новый пользователь в боте</b>\n\n"
    "<b>Имя:</b> {first_name}\n"
    "<b>Username:</b> {username}\n"
    "<b>ID:</b> {telegram_id}\n"
    "<b>Дата:</b> {created_at}"
)

SCHEDULE_MENU_TEXT = (
    "<b>Отложенная публикация ⏰</b>\n\n"
    "Выбери время публикации или введи своё 👇"
)

SCHEDULE_MANUAL_TEXT = (
    "<b>Введи дату и время публикации</b>\n\n"
    "Формат: <code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n"
    "Пример: <code>30.03.2026 18:45</code>"
)

SCHEDULE_INVALID_FORMAT_TEXT = (
    "<b>Неверный формат даты</b>\n\n"
    "<i>Используй формат: ДД.ММ.ГГГГ ЧЧ:ММ</i>"
)

SCHEDULE_PAST_DATE_TEXT = (
    "<b>Дата уже прошла</b>\n\n"
    "<i>Выбери время в будущем</i>"
)

SCHEDULE_NOT_FOUND_TEXT = "Публикация не запланирована"

SCHEDULE_CANCELLED_TEXT = (
    "<b>✅ Планирование отменено</b>\n\n"
    "Пост снова доступен для обычной публикации."
)

SCHEDULED_POST_PUBLISHED_TEXT = (
    "<b>⏰ Запланированный пост опубликован</b>\n\n"
    "<b>Заявка:</b> #{post_id}"
)


def build_schedule_success_text(display_value: str) -> str:
    return (
        "<b>✅ Публикация запланирована</b>\n\n"
        f"<b>Дата:</b> {escape(display_value)}"
    )


def build_submission_summary(caption: str | None, publish_mode_label: str) -> str:
    caption_label = escape(caption) if caption else "без подписи"
    mode_label = escape(publish_mode_label)
    return (
        "<b>Проверь предложку:</b>\n\n"
        "Фото: ✅\n"
        f"Подпись: {caption_label}\n"
        f"Формат: {mode_label}"
    )


def build_broadcast_preview(text: str | None, has_photo: bool) -> str:
    body = escape(text) if text else "<i>без текста</i>"
    photo_line = "✅" if has_photo else "—"
    return (
        "<b>Проверь рассылку:</b>\n\n"
        f"<b>Фото:</b> {photo_line}\n"
        f"<b>Текст:</b>\n{body}"
    )
