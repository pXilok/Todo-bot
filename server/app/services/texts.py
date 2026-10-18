"""Все пользовательские тексты бота.

Сообщения отправляются без parse_mode, поэтому пользовательский ввод экранировать не нужно.
"""

from typing import Final

from app.services.time_parser import TimeParseErrorReason

# Reply-клавиатура. Эти же строки FSM распознаёт как навигацию.
BTN_ADD: Final = "➕ Добавить задачу"
BTN_LIST: Final = "📋 Мои задачи"
BTN_SETTINGS: Final = "⚙️ Настройки"
BTN_STATS: Final = "📊 Статистика"
BTN_HELP: Final = "❓ Помощь"
BTN_CANCEL: Final = "❌ Отмена"

# Inline-кнопки
INLINE_DONE: Final = "✅ {task_id}"
INLINE_REMIND: Final = "⏰ {task_id}"
INLINE_DELETE: Final = "🗑 {task_id}"
INLINE_DELETE_CONFIRM: Final = "🗑 Да, удалить"
INLINE_DELETE_CANCEL: Final = "↩️ Нет, оставить"
INLINE_SET_REMINDER: Final = "⏰ Напомнить"
INLINE_SHOW_LIST: Final = "📋 К списку"
INLINE_ADD_MORE: Final = "➕ Ещё задачу"
INLINE_TIMEZONE: Final = "🕐 Часовой пояс"
INLINE_REMINDERS_ON: Final = "🔔 Напоминания: вкл"
INLINE_REMINDERS_OFF: Final = "🔕 Напоминания: выкл"
INLINE_BACK: Final = "⬅️ В меню"

WELCOME: Final = (
    "Привет, {name}! Я помогу вести список дел и напомню о важном.\n\n"
    "Выберите действие на клавиатуре ниже или наберите /help."
)
DEFAULT_NAME: Final = "друг"
QUICK_START: Final = "Быстрый старт:"
HELP: Final = (
    "Что я умею:\n"
    f"• {BTN_ADD} — новая задача\n"
    f"• {BTN_LIST} — список, отметка выполнения, напоминания, удаление\n"
    f"• {BTN_SETTINGS} — часовой пояс и напоминания\n\n"
    "Команды:\n"
    "/start — начать заново\n"
    "/help — эта справка\n"
    "/settings — настройки\n"
    "/stats — ваша статистика\n"
    "/cancel — отменить текущее действие"
)
MAIN_MENU: Final = "Главное меню."
CANCELLED: Final = "Действие отменено. Вы в главном меню."
WHAT_NEXT: Final = "Что дальше?"

ASK_TASK_TITLE: Final = "Напишите текст задачи (до {max_len} символов)."
TASK_TITLE_EMPTY: Final = "Текст задачи не может быть пустым. Напишите текст или нажмите «Отмена»."
TASK_TITLE_TOO_LONG: Final = "Слишком длинно: {length} из {max_len} символов. Сократите текст."
TASK_ADDED: Final = "Задача #{task_id} добавлена: {title}"

TASK_LIST_EMPTY: Final = f"Список задач пуст. Нажмите «{BTN_ADD}», чтобы добавить первую."
TASK_LIST_HEADER: Final = "Ваши задачи (активных: {pending}, выполнено: {done}):"
TASK_LIST_TRUNCATED: Final = "Показаны первые {shown} из {total}."
TASK_LIST_HINT: Final = "Кнопки: ✅ — выполнено, ⏰ — напоминание, 🗑 — удалить."
TASK_LINE_PENDING: Final = "⬜ #{task_id} {title}"
TASK_LINE_DONE: Final = "✅ #{task_id} {title}"
TASK_LINE_REMINDER: Final = "  ⏰ {when}"

TASK_NOT_FOUND: Final = "Задача не найдена. Возможно, она уже удалена."
TASK_ALREADY_DONE: Final = "Задача #{task_id} уже выполнена."
TASK_MARKED_DONE: Final = "Отлично, задача #{task_id} выполнена."
CONFIRM_DELETE: Final = "Удалить задачу #{task_id} «{title}»?"
TASK_DELETED: Final = "Задача #{task_id} удалена."
DELETE_USE_BUTTONS: Final = "Подтвердите удаление кнопками под сообщением или нажмите «Отмена»."

ASK_REMINDER: Final = (
    "Когда напомнить о задаче #{task_id} «{title}»?\n\n"
    "Форматы:\n"
    "• 18:30 — сегодня (или завтра, если время прошло)\n"
    "• 25.12 09:00 или 25.12.2026 09:00\n"
    "• +30m, +2h, +1d — через 30 минут, 2 часа, 1 день\n\n"
    "Ваш часовой пояс: {tz}."
)
REMINDER_SET: Final = "Готово, напомню {when} ({tz})."
REMINDER_DISABLED_WARNING: Final = (
    "Внимание: напоминания выключены в /settings, уведомление не придёт, пока вы их не включите."
)
REMINDER_FOR_DONE_TASK: Final = "Задача #{task_id} уже выполнена, напоминание не нужно."
REMINDER_MESSAGE: Final = "⏰ Напоминание: {title} (задача #{task_id})"

TIME_PARSE_ERRORS: Final[dict[TimeParseErrorReason, str]] = {
    TimeParseErrorReason.INVALID_FORMAT: "Не понял формат времени. Примеры: 18:30, 25.12 09:00, +2h.",
    TimeParseErrorReason.INVALID_DATE: "Такой даты или времени не существует. Проверьте числа.",
    TimeParseErrorReason.IN_PAST: "Это время уже прошло. Укажите момент в будущем.",
    TimeParseErrorReason.TOO_FAR: "Слишком далеко: напоминание можно поставить максимум на 2 года вперёд.",
    TimeParseErrorReason.OUT_OF_RANGE: "Значение вне допустимого диапазона.",
}

SETTINGS: Final = "Настройки:\n• Часовой пояс: {tz}\n• Напоминания: {reminders}"
SETTINGS_ON: Final = "включены"
SETTINGS_OFF: Final = "выключены"
ASK_TIMEZONE: Final = "Отправьте смещение от UTC, например: +3, -5, +5:30 или UTC+3."
TIMEZONE_INVALID: Final = (
    "Не удалось распознать часовой пояс. Допустимо от UTC-12 до UTC+14, например +3 или -4:30."
)
TIMEZONE_SAVED: Final = "Часовой пояс сохранён: {tz}."

USER_STATS: Final = (
    "📊 Ваша статистика:\n"
    "• Всего задач: {total}\n"
    "• Выполнено: {done}\n"
    "• Активных: {pending}\n"
    "• Ждут напоминания: {with_reminder}\n"
    "• С нами с {since}"
)

UNKNOWN_COMMAND: Final = "Неизвестная команда. Список команд: /help."
UNKNOWN_TEXT: Final = "Не понял сообщение. Воспользуйтесь кнопками меню или /help."
UNKNOWN_CALLBACK: Final = f"Эта кнопка устарела. Откройте список заново: «{BTN_LIST}»."