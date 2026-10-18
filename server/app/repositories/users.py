"""Репозиторий пользователей."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


class UserRepository:
    """Чтение и upsert пользователей."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: int) -> User | None:
        """Пользователь по Telegram id."""
        return await self._session.get(User, user_id)

    async def upsert(
        self,
        *,
        user_id: int,
        username: str | None,
        first_name: str | None,
        chat_id: int,
        now: datetime,
    ) -> tuple[User, bool]:
        """Создать пользователя или обновить профиль и last_seen_at.

        Returns:
            Пару (пользователь, создан_ли_сейчас).
        """
        user = await self.get(user_id)
        if user is None:
            user = User(
                id=user_id,
                username=username,
                first_name=first_name,
                chat_id=chat_id,
                created_at=now,
                last_seen_at=now,
            )
            self._session.add(user)
            await self._session.flush()
            return user, True

        user.username = username
        user.first_name = first_name
        user.chat_id = chat_id
        user.last_seen_at = now
        return user, False

    async def count(self) -> int:
        """Общее число пользователей."""
        return int(await self._session.scalar(select(func.count()).select_from(User)) or 0)

    async def count_active_since(self, since: datetime) -> int:
        """Число пользователей, писавших боту после момента since."""
        stmt = select(func.count()).select_from(User).where(User.last_seen_at >= since)
        return int(await self._session.scalar(stmt) or 0)

    async def list_chat_ids(self) -> list[int]:
        """chat_id всех пользователей (для рассылки)."""
        result = await self._session.scalars(select(User.chat_id).order_by(User.id))
        return list(result.all())