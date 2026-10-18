"""Карточка пользователя для админского API."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import BotState
from app.repositories import Repositories
from app.schemas.users import UserOut, UserSettingsOut, UserTaskCounters


class UserService:
    """Собирает UserOut из нескольких репозиториев."""

    def __init__(self, session: AsyncSession, *, default_tz_offset_minutes: int) -> None:
        self._repos = Repositories.from_session(session)
        self._default_tz_offset_minutes = default_tz_offset_minutes

    async def get_card(self, user_id: int) -> UserOut | None:
        """Карточка пользователя или None, если такого нет."""
        user = await self._repos.users.get(user_id)
        if user is None:
            return None

        settings = await self._repos.settings.get(user_id)
        state_row = await self._repos.states.get(user_id)
        counters = await self._repos.tasks.counters_for_user(user_id)

        return UserOut(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            chat_id=user.chat_id,
            created_at=user.created_at,
            last_seen_at=user.last_seen_at,
            state=state_row.state if state_row else BotState.MAIN_MENU,
            settings=(
                UserSettingsOut.model_validate(settings)
                if settings
                else UserSettingsOut(
                    tz_offset_minutes=self._default_tz_offset_minutes, reminders_enabled=True
                )
            ),
            tasks=UserTaskCounters(
                total=counters.total,
                done=counters.done,
                pending=counters.pending,
                with_reminder=counters.with_reminder,
            ),
            messages_total=await self._repos.messages.count_for_user(user_id),
        )