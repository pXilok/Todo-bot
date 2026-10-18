"""Репозиторий обработанных событий (основа идемпотентности)."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ProcessedEvent


class ProcessedEventRepository:
    """Регистрация пар (platform, update_id) через UNIQUE-ограничение."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def try_register(self, *, platform: str, update_id: int, now: datetime) -> bool:
        """Зарегистрировать событие.

        Должна быть первой записью в транзакции. При дубле откатывается вся сессия,
        а более ранних изменений, которые можно потерять, на этот момент нет.
        SAVEPOINT здесь сознательно не используется: в pysqlite/aiosqlite RELEASE
        внешнего savepoint коммитит транзакцию, и регистрация события ушла бы
        в БД отдельно от бизнес-изменений.

        Returns:
            True для нового события, False для повторной доставки.
        """
        self._session.add(ProcessedEvent(platform=platform, update_id=update_id, processed_at=now))
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            return False
        return True

    async def count(self) -> int:
        """Сколько событий обработано."""
        stmt = select(func.count()).select_from(ProcessedEvent)
        return int(await self._session.scalar(stmt) or 0)