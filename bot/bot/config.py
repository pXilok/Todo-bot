"""Настройки бота из файла bot/.env или переменных окружения."""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    """Конфигурация клиента. Токены обязательны и берутся из окружения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: SecretStr
    service_token: SecretStr = Field(min_length=16)
    server_url: str = "http://127.0.0.1:8000"
    outbox_poll_interval: float = Field(default=5.0, gt=0)
    http_timeout_seconds: float = Field(default=10.0, gt=0)
    http_retries: int = Field(default=3, ge=1, le=10)
    log_level: str = "INFO"


def load_settings() -> BotSettings:
    """Читает настройки из окружения и .env."""
    return BotSettings()  # type: ignore[call-arg]