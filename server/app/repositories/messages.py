"""Репозиторий истории сообщений."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import MessageDirection
from app.db.models import Message


class MessageRepository:
    """Журнал входящих и исходящих сообщений."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        user_id: int,
        direction: MessageDirection,
        text: str | None,
        callback_data: str | None,
        now: datetime,
    ) -> None:
        """Записать сообщение в историю."""
        self._session.add(
            Message(
                user_id=user_id,
                direction=direction,
                text=text,
                callback_data=callback_data,
                created_at=now,
            )
        )

    async def count(self) -> int:
        """Всего сообщений."""
        return int(await self._session.scalar(select(func.count()).select_from(Message)) or 0)

    async def count_for_user(self, user_id: int) -> int:
        """Сообщений у пользователя (в обе стороны)."""
        stmt = select(func.count()).select_from(Message).where(Message.user_id == user_id)
        return int(await self._session.scalar(stmt) or 0)