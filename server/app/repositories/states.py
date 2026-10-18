"""Репозиторий FSM-состояний пользователей."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import BotState
from app.db.models import UserState


class UserStateRepository:
    """Текущее состояние диалога и связанные с ним данные."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: int) -> UserState | None:
        """Состояние пользователя или None, если диалог ещё не начат."""
        return await self._session.get(UserState, user_id)

    async def save(self, user_id: int, state: BotState, data: dict[str, Any]) -> None:
        """Upsert состояния.

        Словарь копируется: так SQLAlchemy гарантированно видит изменение JSON-колонки.
        """
        row = await self.get(user_id)
        if row is None:
            self._session.add(UserState(user_id=user_id, state=state, data=dict(data)))
            return
        row.state = state
        row.data = dict(data)