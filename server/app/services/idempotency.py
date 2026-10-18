"""Идемпотентная обработка событий по (platform, update_id)."""

import logging
from datetime import datetime

from app.repositories.processed_events import ProcessedEventRepository

logger = logging.getLogger(__name__)


class IdempotencyService:
    """Отсекает повторные доставки одного и того же update.

    Гарантию даёт UNIQUE(platform, update_id). При конкурентной доставке на PostgreSQL
    второй INSERT ждёт commit первого и падает с IntegrityError. Если первая транзакция
    откатилась (ошибка в обработчике), запись не сохраняется и повтор обработается заново.
    """

    def __init__(self, repository: ProcessedEventRepository) -> None:
        self._repository = repository

    async def register(self, *, platform: str, update_id: int, now: datetime) -> bool:
        """True, если событие новое и его нужно обработать."""
        is_new = await self._repository.try_register(
            platform=platform, update_id=update_id, now=now
        )
        if not is_new:
            logger.info("Duplicate event skipped: platform=%s update_id=%s", platform, update_id)
        return is_new