"""Разбор времени напоминаний и часовых поясов из пользовательского ввода."""

import re
from datetime import UTC, datetime, timedelta, timezone
from enum import StrEnum
from typing import Final

MAX_REMINDER_AHEAD: Final = timedelta(days=730)
MIN_TZ_OFFSET_MINUTES: Final = -12 * 60
MAX_TZ_OFFSET_MINUTES: Final = 14 * 60
DISPLAY_DATETIME_FORMAT: Final = "%d.%m.%Y %H:%M"
DISPLAY_DATE_FORMAT: Final = "%d.%m.%Y"

_RELATIVE_RE: Final = re.compile(r"^\+\s*(?P<amount>\d{1,4})\s*(?P<unit>[mhdмчд])$")
_TIME_RE: Final = re.compile(r"^(?P<hour>\d{1,2}):(?P<minute>\d{2})$")
_DATE_TIME_RE: Final = re.compile(
    r"^(?P<day>\d{1,2})\.(?P<month>\d{1,2})(?:\.(?P<year>\d{4}))?\s+"
    r"(?P<hour>\d{1,2}):(?P<minute>\d{2})$"
)
_TZ_RE: Final = re.compile(
    r"^(?:utc|gmt)?\s*(?P<sign>[+\-−])?\s*(?P<hours>\d{1,2})(?::?(?P<minutes>\d{2}))?$"
)
_UNIT_DELTAS: Final[dict[str, timedelta]] = {
    "m": timedelta(minutes=1),
    "м": timedelta(minutes=1),
    "h": timedelta(hours=1),
    "ч": timedelta(hours=1),
    "d": timedelta(days=1),
    "д": timedelta(days=1),
}
_NEGATIVE_SIGNS: Final = frozenset({"-", "−"})


class TimeParseErrorReason(StrEnum):
    """Причина, по которой не удалось разобрать ввод."""

    INVALID_FORMAT = "invalid_format"
    INVALID_DATE = "invalid_date"
    IN_PAST = "in_past"
    TOO_FAR = "too_far"
    OUT_OF_RANGE = "out_of_range"


class TimeParseError(ValueError):
    """Ошибка разбора с машиночитаемой причиной."""

    def __init__(self, reason: TimeParseErrorReason) -> None:
        super().__init__(reason.value)
        self.reason = reason


def _tz(offset_minutes: int) -> timezone:
    return timezone(timedelta(minutes=offset_minutes))


def _local(year: int, month: int, day: int, hour: int, minute: int, tz: timezone) -> datetime:
    try:
        return datetime(year, month, day, hour, minute, tzinfo=tz)
    except ValueError as exc:
        raise TimeParseError(TimeParseErrorReason.INVALID_DATE) from exc


def parse_remind_at(raw: str, *, now: datetime, tz_offset_minutes: int) -> datetime:
    """Разобрать время напоминания.

    Форматы: «ЧЧ:ММ» (сегодня, а если время прошло, то завтра), «ДД.ММ ЧЧ:ММ»
    (если дата прошла, то в следующем году), «ДД.ММ.ГГГГ ЧЧ:ММ», «+30m / +2h / +1d»
    (допустимы и русские единицы м/ч/д).

    Returns:
        Момент напоминания в UTC.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")

    text = raw.strip().lower()
    tz = _tz(tz_offset_minutes)
    local_now = now.astimezone(tz)

    if match := _RELATIVE_RE.match(text):
        amount = int(match["amount"])
        if amount == 0:
            raise TimeParseError(TimeParseErrorReason.IN_PAST)
        candidate = now + _UNIT_DELTAS[match["unit"]] * amount
    elif match := _TIME_RE.match(text):
        hour, minute = int(match["hour"]), int(match["minute"])
        candidate = _local(local_now.year, local_now.month, local_now.day, hour, minute, tz)
        if candidate <= local_now:
            candidate += timedelta(days=1)
    elif match := _DATE_TIME_RE.match(text):
        day, month = int(match["day"]), int(match["month"])
        hour, minute = int(match["hour"]), int(match["minute"])
        explicit_year = match["year"] is not None
        year = int(match["year"]) if explicit_year else local_now.year
        candidate = _local(year, month, day, hour, minute, tz)
        if not explicit_year and candidate <= local_now:
            candidate = _local(year + 1, month, day, hour, minute, tz)
    else:
        raise TimeParseError(TimeParseErrorReason.INVALID_FORMAT)

    if candidate <= now:
        raise TimeParseError(TimeParseErrorReason.IN_PAST)
    if candidate - now > MAX_REMINDER_AHEAD:
        raise TimeParseError(TimeParseErrorReason.TOO_FAR)
    return candidate.astimezone(UTC)


def parse_tz_offset(raw: str) -> int:
    """Разобрать смещение от UTC: «+3», «-5», «5:30», «UTC+3», «GMT-2».

    Returns:
        Смещение в минутах в диапазоне UTC−12…UTC+14.
    """
    match = _TZ_RE.match(raw.strip().lower())
    if match is None:
        raise TimeParseError(TimeParseErrorReason.INVALID_FORMAT)

    hours = int(match["hours"])
    minutes = int(match["minutes"] or 0)
    if minutes >= 60:
        raise TimeParseError(TimeParseErrorReason.INVALID_FORMAT)

    total = hours * 60 + minutes
    if match["sign"] in _NEGATIVE_SIGNS:
        total = -total
    if not MIN_TZ_OFFSET_MINUTES <= total <= MAX_TZ_OFFSET_MINUTES:
        raise TimeParseError(TimeParseErrorReason.OUT_OF_RANGE)
    return total


def format_tz_offset(offset_minutes: int) -> str:
    """180 → «UTC+3», 330 → «UTC+5:30», -270 → «UTC-4:30»."""
    sign = "+" if offset_minutes >= 0 else "-"
    hours, minutes = divmod(abs(offset_minutes), 60)
    return f"UTC{sign}{hours}" + (f":{minutes:02d}" if minutes else "")


def format_local(
    moment: datetime, offset_minutes: int, fmt: str = DISPLAY_DATETIME_FORMAT
) -> str:
    """Отформатировать UTC-момент в локальном времени пользователя."""
    return moment.astimezone(_tz(offset_minutes)).strftime(fmt)