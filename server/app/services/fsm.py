"""Конечный автомат: выбор обработчика по паре (состояние, ввод).

Приоритет маршрутизации:
1. callback → таблица callback-действий (работают из любого состояния);
2. /команда → таблица команд (глобальные);
3. текст кнопки reply-меню → навигация (глобальная);
4. текст в состоянии, ожидающем ввод → обработчик состояния;
5. иначе fallback.
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from app.core.constants import BotState, Command, EventType
from app.services import texts
from app.services.callbacks import CallbackAction
from app.services.handlers import commands, settings, tasks
from app.services.handlers.base import Handler, HandlerContext, HandlerResult

_BOT_MENTION_SEPARATOR: Final = "@"


def _parse_command(text: str) -> Command | None:
    """«/Start@my_bot arg» → Command.START. Если это не команда, возвращает None."""
    if not text.startswith("/"):
        return None
    token = text.split(maxsplit=1)[0].split(_BOT_MENTION_SEPARATOR, 1)[0].lower()
    try:
        return Command(token)
    except ValueError:
        return None


class FiniteStateMachine:
    """Неизменяемые таблицы переходов. Один экземпляр на приложение, хранится в app.state."""

    def __init__(self) -> None:
        self._commands: Mapping[Command, Handler] = MappingProxyType({
            Command.START: commands.handle_start,
            Command.HELP: commands.handle_help,
            Command.SETTINGS: settings.show_settings,
            Command.STATS: commands.handle_user_stats,
            Command.CANCEL: commands.handle_cancel,
        })
        self._menu_buttons: Mapping[str, Handler] = MappingProxyType({
            texts.BTN_ADD: tasks.start_add_task,
            texts.BTN_LIST: tasks.list_tasks,
            texts.BTN_SETTINGS: settings.show_settings,
            texts.BTN_STATS: commands.handle_user_stats,
            texts.BTN_HELP: commands.handle_help,
            texts.BTN_CANCEL: commands.handle_cancel,
        })
        self._callbacks: Mapping[CallbackAction, Handler] = MappingProxyType({
            CallbackAction.MENU_MAIN: commands.handle_main_menu,
            CallbackAction.MENU_ADD: tasks.start_add_task,
            CallbackAction.MENU_LIST: tasks.list_tasks,
            CallbackAction.TASK_DONE: tasks.mark_task_done,
            CallbackAction.TASK_REMIND: tasks.ask_reminder_time,
            CallbackAction.TASK_DELETE: tasks.ask_delete_confirmation,
            CallbackAction.TASK_DELETE_CONFIRM: tasks.confirm_delete,
            CallbackAction.TASK_DELETE_CANCEL: tasks.cancel_delete,
            CallbackAction.SETTINGS_TIMEZONE: settings.ask_timezone,
            CallbackAction.SETTINGS_TOGGLE_REMINDERS: settings.toggle_reminders,
        })
        self._state_text: Mapping[BotState, Handler] = MappingProxyType({
            BotState.ADD_TASK: tasks.receive_task_title,
            BotState.SET_REMINDER: tasks.receive_reminder_time,
            BotState.DELETE_TASK: tasks.delete_expects_buttons,
            BotState.SETTINGS_TIMEZONE: settings.receive_timezone,
        })

    def route(self, ctx: HandlerContext) -> Handler:
        """Выбрать обработчик для события в текущем состоянии."""
        if ctx.event.type == EventType.CALLBACK:
            if ctx.callback is None:
                return commands.handle_unknown_callback
            return self._callbacks.get(ctx.callback.action, commands.handle_unknown_callback)

        text = ctx.text
        if text.startswith("/"):
            command = _parse_command(text)
            return self._commands[command] if command else commands.handle_unknown_command

        if handler := self._menu_buttons.get(text):
            return handler

        return self._state_text.get(ctx.state, commands.handle_unknown_text)

    async def dispatch(self, ctx: HandlerContext) -> tuple[Handler, HandlerResult]:
        """Выполнить обработчик. Сам обработчик тоже возвращается, чтобы его можно было залогировать."""
        handler = self.route(ctx)
        return handler, await handler(ctx)