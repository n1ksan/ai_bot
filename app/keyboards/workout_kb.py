"""Inline keyboards for workout actions and completion feedback."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

CB_WORKOUT_EASIER = "workout:easier"
CB_WORKOUT_HARDER = "workout:harder"
CB_WORKOUT_CHOOSE = "workout:choose"

CB_COMPLETED_PREFIX = "workout:completed:"
CB_FEEL_PREFIX = "workout:feel:"
CB_REASON_PREFIX = "workout:reason:"

CB_WORKOUT_BACK_TO_SURVEY = "workout:back:survey"
CB_WORKOUT_BACK_TO_WORKOUT = "workout:back:workout"
CB_WORKOUT_BACK_TO_COMPLETED = "workout:back:completed"


def workout_actions_keyboard(can_adjust: bool) -> InlineKeyboardMarkup:
    """Build keyboard for workout adjustments and final selection."""

    builder = InlineKeyboardBuilder()
    if can_adjust:
        builder.button(text="⬇️ Сделать легче", callback_data=CB_WORKOUT_EASIER)
        builder.button(text="⬆️ Сделать сложнее", callback_data=CB_WORKOUT_HARDER)
    builder.button(text="✅ Выбрать эту тренировку", callback_data=CB_WORKOUT_CHOOSE)
    builder.button(text="🔙 Назад", callback_data=CB_WORKOUT_BACK_TO_SURVEY)
    builder.adjust(2 if can_adjust else 1, 1, 1)
    return builder.as_markup()


def completion_status_keyboard() -> InlineKeyboardMarkup:
    """Build Yes/No keyboard for workout completion confirmation."""

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да", callback_data=f"{CB_COMPLETED_PREFIX}yes")
    builder.button(text="❌ Нет", callback_data=f"{CB_COMPLETED_PREFIX}no")
    builder.button(text="🔙 Назад", callback_data=CB_WORKOUT_BACK_TO_WORKOUT)
    builder.adjust(2, 1)
    return builder.as_markup()


def perceived_difficulty_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for perceived difficulty feedback."""

    builder = InlineKeyboardBuilder()
    builder.button(text="Слишком легко", callback_data=f"{CB_FEEL_PREFIX}too_easy")
    builder.button(text="В самый раз", callback_data=f"{CB_FEEL_PREFIX}just_right")
    builder.button(text="Слишком тяжело", callback_data=f"{CB_FEEL_PREFIX}too_hard")
    builder.button(text="🔙 Назад", callback_data=CB_WORKOUT_BACK_TO_COMPLETED)
    builder.adjust(1)
    return builder.as_markup()


def skip_reason_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for workout skip reason."""

    builder = InlineKeyboardBuilder()
    builder.button(text="Не было времени", callback_data=f"{CB_REASON_PREFIX}no_time")
    builder.button(text="Слишком тяжело", callback_data=f"{CB_REASON_PREFIX}too_hard")
    builder.button(text="Другое", callback_data=f"{CB_REASON_PREFIX}other")
    builder.button(text="🔙 Назад", callback_data=CB_WORKOUT_BACK_TO_COMPLETED)
    builder.adjust(1)
    return builder.as_markup()
