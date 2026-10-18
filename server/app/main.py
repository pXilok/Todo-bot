"""Фабрика приложения. Запуск: uvicorn app.main:create_app --factory."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy.engine import make_url

from app import __version__
from app.api import health
from app.api.router import api_router
from app.core.config import Settings, load_settings
from app.core.logging import setup_logging
from app.db.session import Database

logger = logging.getLogger(__name__)


def _ensure_sqlite_directory(database_url: str) -> None:
    """Создаёт каталог под файл SQLite (в Docker это смонтированный volume)."""
    db_path = make_url(database_url).database
    if db_path and db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)


def create_app(settings: Settings | None = None, database: Database | None = None) -> FastAPI:
    """Создаёт приложение. Настройки и БД можно передать снаружи (тесты)."""
    settings = settings or load_settings()
    setup_logging(settings.log_level)

    if database is None:
        if settings.is_sqlite:
            _ensure_sqlite_directory(settings.database_url)
        database = Database(settings.database_url, echo=settings.db_echo)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("Server started (env=%s, version=%s)", settings.environment, __version__)
        yield
        await database.dispose()
        logger.info("Server stopped")

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Сервер бизнес-логики Telegram-бота: Todo-лист с напоминаниями.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.database = database

    app.include_router(health.router)
    app.include_router(api_router, prefix=settings.api_prefix)
    return app