"""Сценарии работы с задачами: добавление, список, выполнение, удаление, напоминание."""

import logging
from typing import Final

from app.core.constants import BotState
from app.db.models import Task
from app.schemas.actions import ButtonsAction, ReplyKeyboardAction
from app.services import texts
from app.services.handlers.base import (
    STATE_DATA_TASK_ID,
    HandlerContext,
    HandlerResult,
    show_or_edit,
    stay,
    to_main_menu,
)
from app.services.keyboards import (
    after_add_buttons,
    cancel_keyboard,
    delete_confirm_buttons,
    main_menu_keyboard,
    task_list_buttons,
)
from app.services.time_parser import (
    TimeParseError,
    format_local,
    format_tz_offset,
    parse_remind_at,
)

logger = logging.getLogger(__name__)

# Обрезка названий в списке, чтобы страница укладывалась в 4096 символов Telegram.
LIST_TITLE_MAX_LENGTH: Final = 80
ELLIPSIS: Final = "…"


def _shorten(title: str, limit: int = LIST_TITLE_MAX_LENGTH) -> str:
    return title if len(title) <= limit else title[: limit - 1] + ELLIPSIS


async def _task_from_callback(ctx: HandlerContext) -> Task | None:
    task_id = ctx.callback_arg
    if task_id is None:
        return None
    return await ctx.repos.tasks.get_for_user(task_id, ctx.user.id)


async def _render_task_list(ctx: HandlerContext, *, notice: str | None = None) -> HandlerResult:
    """Показать (или перерисовать на месте) список задач."""
    tasks = await ctx.repos.tasks.list_for_user(ctx.user.id, limit=ctx.limits.tasks_page_size)
    if not tasks:
        body = texts.TASK_LIST_EMPTY
    else:
        counters = await ctx.repos.tasks.counters_for_user(ctx.user.id)
        lines = [texts.TASK_LIST_HEADER.format(pending=counters.pending, done=counters.done), ""]
        for task in tasks:
            template = texts.TASK_LINE_DONE if task.is_done else texts.TASK_LINE_PENDING
            line = template.format(task_id=task.id, title=_shorten(task.title))
            if task.remind_at is not None and task.reminded_at is None and not task.is_done:
                when = format_local(task.remind_at, ctx.settings.tz_offset_minutes)
                line += texts.TASK_LINE_REMINDER.format(when=when)
            lines.append(line)
        if counters.total > len(tasks):
            lines += ["", texts.TASK_LIST_TRUNCATED.format(shown=len(tasks), total=counters.total)]
        lines += ["", texts.TASK_LIST_HINT]
        body = "\n".join(lines)

    text = f"{notice}\n\n{body}" if notice else body
    return HandlerResult(
        actions=[show_or_edit(ctx, text, task_list_buttons(tasks))],
        state=BotState.LIST_TASKS,
    )


async def start_add_task(ctx: HandlerContext) -> HandlerResult:
    """Перейти к вводу текста новой задачи."""
    prompt = texts.ASK_TASK_TITLE.format(max_len=ctx.limits.task_title_max_length)
    return HandlerResult(
        actions=[ReplyKeyboardAction(text=prompt, keyboard=cancel_keyboard())],
        state=BotState.ADD_TASK,
    )


async def receive_task_title(ctx: HandlerContext) -> HandlerResult:
    """ADD_TASK + текст: проверить и сохранить задачу."""
    title = " ".join(ctx.text.split())
    max_len = ctx.limits.task_title_max_length
    if not title:
        return stay(ctx, texts.TASK_TITLE_EMPTY)
    if len(title) > max_len:
        return stay(ctx, texts.TASK_TITLE_TOO_LONG.format(length=len(title), max_len=max_len))

    task = await ctx.repos.tasks.create(user_id=ctx.user.id, title=title, now=ctx.now)
    logger.info("Task created: user_id=%s task_id=%s", ctx.user.id, task.id)
    return to_main_menu(
        texts.TASK_ADDED.format(task_id=task.id, title=title),
        ButtonsAction(text=texts.WHAT_NEXT, buttons=after_add_buttons(task.id)),
    )


async def list_tasks(ctx: HandlerContext) -> HandlerResult:
    """Показать список задач."""
    return await _render_task_list(ctx)


async def mark_task_done(ctx: HandlerContext) -> HandlerResult:
    """Кнопка ✅: отметить выполнение и перерисовать список."""
    task = await _task_from_callback(ctx)
    if task is None:
        return await _render_task_list(ctx, notice=texts.TASK_NOT_FOUND)
    if task.is_done:
        return await _render_task_list(ctx, notice=texts.TASK_ALREADY_DONE.format(task_id=task.id))

    await ctx.repos.tasks.mark_done(task, now=ctx.now)
    return await _render_task_list(ctx, notice=texts.TASK_MARKED_DONE.format(task_id=task.id))


async def ask_delete_confirmation(ctx: HandlerContext) -> HandlerResult:
    """Кнопка 🗑: запросить подтверждение."""
    task = await _task_from_callback(ctx)
    if task is None:
        return await _render_task_list(ctx, notice=texts.TASK_NOT_FOUND)

    text = texts.CONFIRM_DELETE.format(task_id=task.id, title=_shorten(task.title))
    return HandlerResult(
        actions=[show_or_edit(ctx, text, delete_confirm_buttons(task.id))],
        state=BotState.DELETE_TASK,
        state_data={STATE_DATA_TASK_ID: task.id},
    )


async def confirm_delete(ctx: HandlerContext) -> HandlerResult:
    """Подтверждение удаления."""
    task = await _task_from_callback(ctx)
    if task is None:
        return await _render_task_list(ctx, notice=texts.TASK_NOT_FOUND)

    task_id = task.id
    await ctx.repos.tasks.delete(task)
    logger.info("Task deleted: user_id=%s task_id=%s", ctx.user.id, task_id)
    return await _render_task_list(ctx, notice=texts.TASK_DELETED.format(task_id=task_id))


async def cancel_delete(ctx: HandlerContext) -> HandlerResult:
    """Отказ от удаления: вернуть список."""
    return await _render_task_list(ctx)


async def delete_expects_buttons(ctx: HandlerContext) -> HandlerResult:
    """DELETE_TASK + текст: подсказать, что нужно нажать кнопку."""
    return stay(ctx, texts.DELETE_USE_BUTTONS)


async def ask_reminder_time(ctx: HandlerContext) -> HandlerResult:
    """Кнопка ⏰: перейти к вводу времени напоминания."""
    task = await _task_from_callback(ctx)
    if task is None:
        return await _render_task_list(ctx, notice=texts.TASK_NOT_FOUND)
    if task.is_done:
        return await _render_task_list(ctx, notice=texts.REMINDER_FOR_DONE_TASK.format(task_id=task.id))

    prompt = texts.ASK_REMINDER.format(
        task_id=task.id,
        title=_shorten(task.title),
        tz=format_tz_offset(ctx.settings.tz_offset_minutes),
    )
    return HandlerResult(
        actions=[ReplyKeyboardAction(text=prompt, keyboard=cancel_keyboard())],
        state=BotState.SET_REMINDER,
        state_data={STATE_DATA_TASK_ID: task.id},
    )


async def receive_reminder_time(ctx: HandlerContext) -> HandlerResult:
    """SET_REMINDER + текст: разобрать время и сохранить напоминание."""
    raw_task_id = ctx.state_data.get(STATE_DATA_TASK_ID)
    task = (
        await ctx.repos.tasks.get_for_user(raw_task_id, ctx.user.id)
        if isinstance(raw_task_id, int)
        else None
    )
    if task is None:
        return to_main_menu(texts.TASK_NOT_FOUND)

    offset = ctx.settings.tz_offset_minutes
    try:
        remind_at = parse_remind_at(ctx.text, now=ctx.now, tz_offset_minutes=offset)
    except TimeParseError as exc:
        return stay(ctx, texts.TIME_PARSE_ERRORS[exc.reason])

    await ctx.repos.tasks.set_reminder(task, remind_at)
    message = texts.REMINDER_SET.format(when=format_local(remind_at, offset), tz=format_tz_offset(offset))
    if not ctx.settings.reminders_enabled:
        message = f"{message}\n\n{texts.REMINDER_DISABLED_WARNING}"
    return HandlerResult(
        actions=[ReplyKeyboardAction(text=message, keyboard=main_menu_keyboard())],
        state=BotState.MAIN_MENU,
    )