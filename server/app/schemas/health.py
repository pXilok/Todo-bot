"""Схема health-check."""

from typing import Literal

from pydantic import BaseModel


class HealthOut(BaseModel):
    """Состояние сервиса и БД."""

    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]
    version: str