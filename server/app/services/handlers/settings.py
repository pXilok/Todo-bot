"""Сценарий настроек: часовой пояс и вкл/выкл напоминаний."""

from app.core.constants import BotState
from app.db.models import UserSettings
from app.schemas.actions import ButtonsAction, ReplyKeyboardAction
from app.services import texts
from app.services.handlers.base import HandlerContext, HandlerResult, show_or_edit, stay
from app.services.keyboards import cancel_keyboard, main_menu_keyboard, settings_buttons
from app.services.time_parser import TimeParseError, format_tz_offset, parse_tz_offset


def _settings_text(settings: UserSettings) -> str:
    return texts.SETTINGS.format(
        tz=format_tz_offset(settings.tz_offset_minutes),
        reminders=texts.SETTINGS_ON if settings.reminders_enabled else texts.SETTINGS_OFF,
    )


async def show_settings(ctx: HandlerContext) -> HandlerResult:
    """/settings или кнопка меню."""
    buttons = settings_buttons(reminders_enabled=ctx.settings.reminders_enabled)
    return HandlerResult(
        actions=[show_or_edit(ctx, _settings_text(ctx.settings), buttons)],
        state=BotState.SETTINGS,
    )


async def ask_timezone(ctx: HandlerContext) -> HandlerResult:
    """Кнопка «Часовой пояс»."""
    return HandlerResult(
        actions=[ReplyKeyboardAction(text=texts.ASK_TIMEZONE, keyboard=cancel_keyboard())],
        state=BotState.SETTINGS_TIMEZONE,
    )


async def receive_timezone(ctx: HandlerContext) -> HandlerResult:
    """SETTINGS_TIMEZONE + текст: сохранить пояс и показать настройки."""
    try:
        offset = parse_tz_offset(ctx.text)
    except TimeParseError:
        return stay(ctx, texts.TIMEZONE_INVALID)

    await ctx.repos.settings.set_timezone(ctx.settings, offset)
    return HandlerResult(
        actions=[
            ReplyKeyboardAction(
                text=texts.TIMEZONE_SAVED.format(tz=format_tz_offset(offset)),
                keyboard=main_menu_keyboard(),
            ),
            ButtonsAction(
                text=_settings_text(ctx.settings),
                buttons=settings_buttons(reminders_enabled=ctx.settings.reminders_enabled),
            ),
        ],
        state=BotState.SETTINGS,
    )


async def toggle_reminders(ctx: HandlerContext) -> HandlerResult:
    """Переключить напоминания и перерисовать меню настроек."""
    await ctx.repos.settings.toggle_reminders(ctx.settings)
    return await show_settings(ctx)