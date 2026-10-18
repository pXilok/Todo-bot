"""Источник времени. Передаётся в сервисы, чтобы в тестах его можно было подменить."""

from collections.abc import Callable
from datetime import UTC, datetime

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    """Текущее время в UTC с tzinfo."""
    return datetime.now(UTC)