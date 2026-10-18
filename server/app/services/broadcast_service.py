"""Рассылка сообщения всем пользователям через outbox."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, utc_now
from app.core.constants import OutboxKind
from app.repositories import OutboxRepository, UserRepository
from app.schemas.admin import BroadcastRequest, BroadcastResponse

logger = logging.getLogger(__name__)


class BroadcastService:
    """Ставит по одной записи outbox на каждого пользователя. Доставкой занимается клиент."""

    def __init__(self, session: AsyncSession, clock: Clock = utc_now) -> None:
        self._session = session
        self._clock = clock
        self._users = UserRepository(session)
        self._outbox = OutboxRepository(session)

    async def broadcast(self, request: BroadcastRequest) -> BroadcastResponse:
        """Поставить рассылку в очередь."""
        try:
            chat_ids = await self._users.list_chat_ids()
            queued = await self._outbox.enqueue_many(
                chat_ids=chat_ids, kind=OutboxKind.BROADCAST, text=request.text, now=self._clock()
            )
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise
        logger.info("Broadcast queued for %s chats", queued)
        return BroadcastResponse(queued=queued)