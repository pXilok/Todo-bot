"""Формат callback_data: «<область>:<действие>[:<id>]»."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

CALLBACK_DATA_MAX_BYTES: Final = 64
_ARG_SEPARATOR: Final = ":"


class CallbackAction(StrEnum):
    """Все допустимые действия inline-кнопок."""

    MENU_MAIN = "menu:main"
    MENU_ADD = "menu:add"
    MENU_LIST = "menu:list"
    TASK_DONE = "task:done"
    TASK_REMIND = "task:remind"
    TASK_DELETE = "task:del"
    TASK_DELETE_CONFIRM = "task:del_ok"
    TASK_DELETE_CANCEL = "task:del_no"
    SETTINGS_TIMEZONE = "set:tz"
    SETTINGS_TOGGLE_REMINDERS = "set:rem"


@dataclass(frozen=True, slots=True)
class ParsedCallback:
    """Разобранная callback_data."""

    action: CallbackAction
    arg: int | None = None


def build_callback(action: CallbackAction, arg: int | None = None) -> str:
    """Собрать callback_data и проверить лимит Telegram в 64 байта."""
    data = action.value if arg is None else f"{action.value}{_ARG_SEPARATOR}{arg}"
    if len(data.encode()) > CALLBACK_DATA_MAX_BYTES:
        raise ValueError(f"callback_data exceeds {CALLBACK_DATA_MAX_BYTES} bytes: {data!r}")
    return data


def parse_callback(data: str) -> ParsedCallback | None:
    """Разобрать callback_data. Для неизвестных или битых данных возвращает None."""
    try:
        return ParsedCallback(CallbackAction(data))
    except ValueError:
        pass

    head, separator, tail = data.rpartition(_ARG_SEPARATOR)
    if not separator or not (tail.isascii() and tail.isdigit()):
        return None
    try:
        action = CallbackAction(head)
    except ValueError:
        return None
    return ParsedCallback(action=action, arg=int(tail))