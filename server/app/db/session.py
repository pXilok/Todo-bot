"""Движок и фабрика сессий. Экземпляр Database живёт в app.state, не в модуле."""

import logging
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)


class Database:
    """Владелец AsyncEngine и фабрики сессий."""

    def __init__(self, url: str, *, echo: bool = False) -> None:
        engine_kwargs: dict[str, Any] = {"echo": echo, "pool_pre_ping": True}
        is_sqlite = url.startswith("sqlite")

        if is_sqlite:
            engine_kwargs["connect_args"] = {"check_same_thread": False}
            if ":memory:" in url:
                # Одно соединение на весь процесс, иначе каждая сессия увидит пустую БД.
                engine_kwargs["poolclass"] = StaticPool

        self.engine: AsyncEngine = create_async_engine(url, **engine_kwargs)
        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            autoflush=False,
        )

        if is_sqlite:
            self._enable_sqlite_foreign_keys()

    def _enable_sqlite_foreign_keys(self) -> None:
        """SQLite по умолчанию игнорирует FK; включаем, чтобы работал ON DELETE CASCADE."""

        @event.listens_for(self.engine.sync_engine, "connect")
        def _set_pragma(dbapi_connection: Any, _: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    async def session(self) -> AsyncIterator[AsyncSession]:
        """Сессия с транзакцией на единицу работы: commit при успехе, rollback при ошибке."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception("Transaction rolled back")
                raise

    async def dispose(self) -> None:
        """Закрывает пул соединений."""
        await self.engine.dispose()