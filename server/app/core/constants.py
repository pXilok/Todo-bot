"""Доменные константы и перечисления. Единственный источник «магических» строк."""

from enum import StrEnum
from typing import Final

TELEGRAM_TEXT_MAX_LENGTH: Final[int] = 4096
TELEGRAM_CALLBACK_DATA_MAX_BYTES: Final[int] = 64
TELEGRAM_BUTTON_TEXT_MAX_LENGTH: Final[int] = 64
ENUM_COLUMN_LENGTH: Final[int] = 32

ADMIN_TOKEN_HEADER: Final[str] = "X-Admin-Token"
SERVICE_TOKEN_HEADER: Final[str] = "X-Service-Token"


class Platform(StrEnum):
    """Платформа-источник события."""

    TELEGRAM = "telegram"


class EventType(StrEnum):
    """Тип нормализованного события."""

    MESSAGE = "message"
    CALLBACK = "callback"


class ActionType(StrEnum):
    """Тип действия, которое клиент должен выполнить."""

    TEXT = "text"
    BUTTONS = "buttons"
    KEYBOARD = "keyboard"
    MEDIA = "media"
    EDIT = "edit"
    STATE = "state"


class MediaType(StrEnum):
    """Тип медиа-вложения."""

    PHOTO = "photo"
    DOCUMENT = "document"


class BotState(StrEnum):
    """Состояния FSM диалога."""

    MAIN_MENU = "MAIN_MENU"
    ADD_TASK = "ADD_TASK"
    LIST_TASKS = "LIST_TASKS"
    DELETE_TASK = "DELETE_TASK"
    SET_REMINDER = "SET_REMINDER"
    SETTINGS = "SETTINGS"
    SETTINGS_TIMEZONE = "SETTINGS_TIMEZONE"


class MessageDirection(StrEnum):
    """Направление сообщения в истории."""

    INCOMING = "in"
    OUTGOING = "out"


class OutboxKind(StrEnum):
    """Тип исходящего отложенного сообщения."""

    REMINDER = "reminder"
    BROADCAST = "broadcast"


class OutboxStatus(StrEnum):
    """Статус записи outbox."""

    PENDING = "pending"
    CLAIMED = "claimed"
    SENT = "sent"
    FAILED = "failed"


class AckStatus(StrEnum):
    """Результат доставки, о котором сообщает клиент."""

    SENT = "sent"
    FAILED = "failed"
class Command(StrEnum):
    """Глобальные команды бота."""

    START = "/start"
    HELP = "/help"
    SETTINGS = "/settings"
    STATS = "/stats"
    CANCEL = "/cancel"