"""Настройки сервера из переменных окружения / .env."""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация приложения. Секреты обязательны и не имеют дефолтов."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Todo Bot Server"
    environment: Literal["dev", "test", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    api_prefix: str = "/api/v1"

    database_url: str = "sqlite+aiosqlite:///./data/bot.db"
    db_echo: bool = False

    admin_token: SecretStr = Field(min_length=16)
    service_token: SecretStr = Field(min_length=16)

    default_tz_offset_minutes: int = Field(default=180, ge=-720, le=840)
    max_task_title_length: int = Field(default=200, ge=1, le=1000)
    tasks_page_size: int = Field(default=10, ge=1, le=50)
    max_active_tasks_per_user: int = Field(default=200, ge=1)

    outbox_batch_size: int = Field(default=50, ge=1, le=500)
    outbox_claim_timeout_seconds: int = Field(default=120, ge=10)
    outbox_max_attempts: int = Field(default=5, ge=1)

    @property
    def is_sqlite(self) -> bool:
        """True, если используется SQLite."""
        return self.database_url.startswith("sqlite")


def load_settings() -> Settings:
    """Создаёт экземпляр настроек. Вызывается один раз в create_app()."""
    return Settings()  # type: ignore[call-arg]  # значения приходят из окружения