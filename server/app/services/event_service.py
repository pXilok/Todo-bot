"""Оркестратор обработки события: идемпотентность, пользователь, FSM, история."""

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, utc_now
from app.core.config import Settings
from app.core.constants import BotState, MessageDirection
from app.repositories import ProcessedEventRepository, Repositories
from app.schemas.events import Action, EventResponse, NormalizedEvent, StateAction
from app.services.fsm import FiniteStateMachine
from app.services.handlers.base import HandlerContext, HandlerLimits
from app.services.idempotency import IdempotencyService

logger = logging.getLogger(__name__)


def _outgoing_text(action: Action) -> str | None:
    """Текст исходящего действия для журнала сообщений, если он есть."""
    text = getattr(action, "text", None)
    return text if isinstance(text, str) else None


class EventService:
    """Обрабатывает одно событие в одной транзакции (unit of work)."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings,
        clock: Clock = utc_now,
    ) -> None:
        self._session = session
        self._fsm = FiniteStateMachine()
        self._default_tz_offset_minutes = settings.default_tz_offset_minutes
        self._limits = HandlerLimits(
            task_title_max_length=settings.max_task_title_length,
            tasks_page_size=settings.tasks_page_size,
        )
        self._clock = clock

    async def handle(self, event: NormalizedEvent) -> EventResponse:
        """Обработать событие и вернуть действия для клиента.

        Ошибка в любом месте откатывает всю транзакцию, включая отметку в processed_events,
        поэтому повторная доставка того же update будет обработана заново.
        """
        now = self._clock()
        repos = Repositories.from_session(self._session)
        idempotency = IdempotencyService(ProcessedEventRepository(self._session))

        try:
            is_new = await idempotency.register(
                platform=event.platform, update_id=event.update_id, now=now
            )
            if not is_new:
                state_row = await repos.states.get(event.user.id)
                return EventResponse(
                    actions=[],
                    state=state_row.state if state_row else BotState.MAIN_MENU,
                    duplicate=True,
                )

            response = await self._handle(repos, event, now)
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            logger.exception("Event processing failed: update_id=%s", event.update_id)
            raise
        return response

    async def _handle(
        self, repos: Repositories, event: NormalizedEvent, now: datetime
    ) -> EventResponse:
        """Основная логика: пользователь, настройки, состояние, обработчик, история."""
        user, created = await repos.users.upsert(
            user_id=event.user.id,
            username=event.user.username,
            first_name=event.user.first_name,
            chat_id=event.chat_id,
            now=now,
        )
        if created:
            logger.info("New user registered: user_id=%s", user.id)

        user_settings = await repos.settings.get_or_create(
            user.id, default_tz_offset_minutes=self._default_tz_offset_minutes
        )
        state_row = await repos.states.get(user.id)
        state = state_row.state if state_row else BotState.MAIN_MENU
        state_data = dict(state_row.data or {}) if state_row else {}

        await repos.messages.add(
            user_id=user.id,
            direction=MessageDirection.IN,
            text=event.text,
            callback_data=event.callback_data,
            now=now,
        )

        ctx = HandlerContext(
            event=event,
            user=user,
            settings=user_settings,
            state=state,
            state_data=state_data,
            now=now,
            repos=repos,
            limits=self._limits,
        )
        handler, result = await self._fsm.dispatch(ctx)

        await repos.states.save(user.id, result.state, result.state_data)
        for action in result.actions:
            if (text := _outgoing_text(action)) is not None:
                await repos.messages.add(
                    user_id=user.id,
                    direction=MessageDirection.OUT,
                    text=text,
                    callback_data=None,
                    now=now,
                )

        logger.info(
            "Event handled: update_id=%s user_id=%s %s -> %s via %s",
            event.update_id,
            user.id,
            state,
            result.state,
            handler.__name__,
        )
        return EventResponse(
            actions=[*result.actions, StateAction(state=result.state)],
            state=result.state,
        )