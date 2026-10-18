"""Репозиторий пользовательских настроек."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserSettings


class UserSettingsRepository:
    """Настройки: часовой пояс и флаг напоминаний."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: int) -> UserSettings | None:
        """Настройки пользователя, если они уже созданы."""
        return await self._session.get(UserSettings, user_id)

    async def get_or_create(self, user_id: int, *, default_tz_offset_minutes: int) -> UserSettings:
        """Вернуть настройки, при отсутствии создать их со значениями по умолчанию."""
        settings = await self.get(user_id)
        if settings is None:
            settings = UserSettings(
                user_id=user_id,
                tz_offset_minutes=default_tz_offset_minutes,
                reminders_enabled=True,
            )
            self._session.add(settings)
            await self._session.flush()
        return settings

    async def set_timezone(self, settings: UserSettings, offset_minutes: int) -> None:
        """Сохранить смещение часового пояса в минутах."""
        settings.tz_offset_minutes = offset_minutes

    async def toggle_reminders(self, settings: UserSettings) -> bool:
        """Инвертировать флаг напоминаний и вернуть новое значение."""
        settings.reminders_enabled = not settings.reminders_enabled
        return settings.reminders_enabled