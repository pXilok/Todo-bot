"""Общие валидаторы схем."""

from app.core.constants import TELEGRAM_CALLBACK_DATA_MAX_BYTES


def validate_callback_data(value: str | None) -> str | None:
    """Telegram ограничивает callback_data 64 байтами (UTF-8), не символами."""
    if value is None:
        return None
    if not value:
        raise ValueError("callback_data must not be empty")
    if len(value.encode("utf-8")) > TELEGRAM_CALLBACK_DATA_MAX_BYTES:
        raise ValueError(f"callback_data exceeds {TELEGRAM_CALLBACK_DATA_MAX_BYTES} bytes")
    return value