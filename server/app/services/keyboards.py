"""Построители клавиатур. Возвращают данные контракта, а не объекты aiogram."""

from collections.abc import Sequence

from app.db.models import Task
from app.schemas.actions import InlineButton
from app.services import texts
from app.services.callbacks import CallbackAction, build_callback

InlineRows = list[list[InlineButton]]


def _button(text: str, action: CallbackAction, arg: int | None = None) -> InlineButton:
    return InlineButton(text=text, callback_data=build_callback(action, arg))


def main_menu_keyboard() -> list[list[str]]:
    """Reply-клавиатура главного меню."""
    return [
        [texts.BTN_ADD, texts.BTN_LIST],
        [texts.BTN_SETTINGS, texts.BTN_STATS],
        [texts.BTN_HELP],
    ]


def cancel_keyboard() -> list[list[str]]:
    """Reply-клавиатура на время ввода."""
    return [[texts.BTN_CANCEL]]


def quick_start_buttons() -> InlineRows:
    """Inline-кнопки под приветствием."""
    return [[
        _button(texts.BTN_ADD, CallbackAction.MENU_ADD),
        _button(texts.BTN_LIST, CallbackAction.MENU_LIST),
    ]]


def after_add_buttons(task_id: int) -> InlineRows:
    """Кнопки после создания задачи."""
    return [
        [_button(texts.INLINE_SET_REMINDER, CallbackAction.TASK_REMIND, task_id)],
        [
            _button(texts.INLINE_ADD_MORE, CallbackAction.MENU_ADD),
            _button(texts.INLINE_SHOW_LIST, CallbackAction.MENU_LIST),
        ],
    ]


def task_list_buttons(tasks: Sequence[Task]) -> InlineRows:
    """По ряду на задачу. У выполненных задач только кнопка удаления."""
    rows: InlineRows = []
    for task in tasks:
        delete = _button(texts.INLINE_DELETE.format(task_id=task.id), CallbackAction.TASK_DELETE, task.id)
        if task.is_done:
            rows.append([delete])
            continue
        rows.append([
            _button(texts.INLINE_DONE.format(task_id=task.id), CallbackAction.TASK_DONE, task.id),
            _button(texts.INLINE_REMIND.format(task_id=task.id), CallbackAction.TASK_REMIND, task.id),
            delete,
        ])
    return rows


def delete_confirm_buttons(task_id: int) -> InlineRows:
    """Подтверждение удаления."""
    return [[
        _button(texts.INLINE_DELETE_CONFIRM, CallbackAction.TASK_DELETE_CONFIRM, task_id),
        _button(texts.INLINE_DELETE_CANCEL, CallbackAction.TASK_DELETE_CANCEL),
    ]]


def settings_buttons(*, reminders_enabled: bool) -> InlineRows:
    """Меню настроек."""
    toggle_text = texts.INLINE_REMINDERS_ON if reminders_enabled else texts.INLINE_REMINDERS_OFF
    return [
        [_button(texts.INLINE_TIMEZONE, CallbackAction.SETTINGS_TIMEZONE)],
        [_button(toggle_text, CallbackAction.SETTINGS_TOGGLE_REMINDERS)],
        [_button(texts.INLINE_BACK, CallbackAction.MENU_MAIN)],
    ]