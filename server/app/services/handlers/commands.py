"""Глобальные команды и fallback-обработчики."""

from app.core.constants import BotState
from app.schemas.actions import ButtonsAction, ReplyKeyboardAction
from app.services import texts
from app.services.handlers.base import HandlerContext, HandlerResult, stay, to_main_menu
from app.services.keyboards import main_menu_keyboard, quick_start_buttons
from app.services.time_parser import DISPLAY_DATE_FORMAT, format_local


async def handle_start(ctx: HandlerContext) -> HandlerResult:
    """/start: приветствие, reply-меню и inline-кнопки быстрого старта."""
    name = ctx.user.first_name or ctx.user.username or texts.DEFAULT_NAME
    return HandlerResult(
        actions=[
            ReplyKeyboardAction(text=texts.WELCOME.format(name=name), keyboard=main_menu_keyboard()),
            ButtonsAction(text=texts.QUICK_START, buttons=quick_start_buttons()),
        ],
        state=BotState.MAIN_MENU,
    )


async def handle_help(ctx: HandlerContext) -> HandlerResult:
    """/help: справка."""
    return to_main_menu(texts.HELP)


async def handle_cancel(ctx: HandlerContext) -> HandlerResult:
    """/cancel или «Отмена»: выход из любого сценария."""
    return to_main_menu(texts.CANCELLED)


async def handle_main_menu(ctx: HandlerContext) -> HandlerResult:
    """Кнопка «В меню»."""
    return to_main_menu(texts.MAIN_MENU)


async def handle_user_stats(ctx: HandlerContext) -> HandlerResult:
    """/stats: личная статистика пользователя."""
    counters = await ctx.repos.tasks.counters_for_user(ctx.user.id)
    text = texts.USER_STATS.format(
        total=counters.total,
        done=counters.done,
        pending=counters.pending,
        with_reminder=counters.with_reminder,
        since=format_local(ctx.user.created_at, ctx.settings.tz_offset_minutes, DISPLAY_DATE_FORMAT),
    )
    return to_main_menu(text)


async def handle_unknown_command(ctx: HandlerContext) -> HandlerResult:
    """Неизвестная /команда: состояние не меняется."""
    return stay(ctx, texts.UNKNOWN_COMMAND)


async def handle_unknown_text(ctx: HandlerContext) -> HandlerResult:
    """Текст, который в текущем состоянии не ожидается."""
    return stay(ctx, texts.UNKNOWN_TEXT)


async def handle_unknown_callback(ctx: HandlerContext) -> HandlerResult:
    """Битая или устаревшая callback_data."""
    return stay(ctx, texts.UNKNOWN_CALLBACK)