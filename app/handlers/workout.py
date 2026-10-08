"""Workout generation, adjustment, and completion feedback handlers."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards.survey_kb import start_survey_keyboard
from app.keyboards.workout_kb import (
    CB_COMPLETED_PREFIX,
    CB_FEEL_PREFIX,
    CB_REASON_PREFIX,
    CB_WORKOUT_BACK_TO_COMPLETED,
    CB_WORKOUT_BACK_TO_SURVEY,
    CB_WORKOUT_BACK_TO_WORKOUT,
    CB_WORKOUT_CHOOSE,
    CB_WORKOUT_EASIER,
    CB_WORKOUT_HARDER,
    completion_status_keyboard,
    perceived_difficulty_keyboard,
    skip_reason_keyboard,
    workout_actions_keyboard,
)
from app.services.openai_service import WorkoutGenerationError, WorkoutPlan, get_openai_service
from app.storage.memory import memory_store
from app.utils.formatters import format_workout_message

router = Router()
logger = logging.getLogger(__name__)

MAX_ADJUSTMENTS = 3

PERCEIVED_DIFFICULTY_OPTIONS: dict[str, str] = {
    "too_easy": "Слишком легко",
    "just_right": "В самый раз",
    "too_hard": "Слишком тяжело",
}

SKIP_REASON_OPTIONS: dict[str, str] = {
    "no_time": "Не было времени",
    "too_hard": "Слишком тяжело",
    "other": "Другое",
}


def _welcome_text() -> str:
    """Return welcome text used when user goes back to survey."""

    return (
        "🏊 Привет! Я ваш ИИ-тренер по плаванию.\n\n"
        "За 4 коротких шага соберу профиль и подготовлю персональную тренировку.\n"
        "Нажмите кнопку ниже, чтобы начать опрос."
    )


def _completion_question_text() -> str:
    """Return completion question text."""

    return "✅ Тренировка сохранена! Вы выполнили её?"


async def _render_workout_message(
    message: Message,
    user_id: int,
    workout: WorkoutPlan,
) -> None:
    """Render workout text and proper action keyboard in place."""

    can_adjust = memory_store.can_adjust_workout(user_id, MAX_ADJUSTMENTS)
    await message.edit_text(
        format_workout_message(workout),
        reply_markup=workout_actions_keyboard(can_adjust=can_adjust),
    )


async def generate_and_render_initial_workout(message: Message, user_id: int) -> None:
    """Generate first workout after survey and display it to user."""

    profile = memory_store.get_profile(user_id)
    if not profile:
        await message.edit_text("Профиль не найден. Запустите заново: /start")
        return

    service = get_openai_service()
    try:
        workout = await service.generate_workout(profile)
    except WorkoutGenerationError as exc:
        logger.error(
            "Initial workout generation failed for user_id=%s: %s",
            user_id,
            exc,
        )
        await message.edit_text(
            "Не удалось сгенерировать тренировку.\n"
            "Проверьте интернет/ключ OpenAI и попробуйте снова через /start."
        )
        return

    memory_store.add_generated_workout(user_id, workout)
    await _render_workout_message(message, user_id, workout)


@router.callback_query(F.data == CB_WORKOUT_BACK_TO_SURVEY)
async def back_to_survey(callback: CallbackQuery, state: FSMContext) -> None:
    """Return from workout screens to the welcome survey screen."""

    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    user_id = callback.from_user.id
    memory_store.reset_session(user_id)
    await state.clear()
    await callback.answer()

    await callback.message.edit_text(
        _welcome_text(),
        reply_markup=start_survey_keyboard(),
    )


@router.callback_query(F.data == CB_WORKOUT_BACK_TO_WORKOUT)
async def back_to_workout(callback: CallbackQuery) -> None:
    """Return from completion question to current workout view."""

    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    user_id = callback.from_user.id
    workout = memory_store.get_current_workout(user_id)
    if not workout:
        await callback.answer("Тренировка не найдена. Запустите /start.", show_alert=True)
        return

    await callback.answer()
    await _render_workout_message(callback.message, user_id, workout)


@router.callback_query(F.data == CB_WORKOUT_BACK_TO_COMPLETED)
async def back_to_completed_question(callback: CallbackQuery) -> None:
    """Return from final feedback step to completion Yes/No step."""

    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    await callback.answer()
    await callback.message.edit_text(
        _completion_question_text(),
        reply_markup=completion_status_keyboard(),
    )


@router.callback_query(F.data.in_({CB_WORKOUT_EASIER, CB_WORKOUT_HARDER}))
async def adjust_workout(callback: CallbackQuery) -> None:
    """Handle easier/harder workout adjustment requests."""

    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    user_id = callback.from_user.id
    if not memory_store.can_adjust_workout(user_id, MAX_ADJUSTMENTS):
        await callback.answer(
            "Лимит корректировок достигнут. Выберите текущую тренировку.",
            show_alert=True,
        )
        try:
            await callback.message.edit_reply_markup(
                reply_markup=workout_actions_keyboard(can_adjust=False)
            )
        except TelegramBadRequest:
            pass
        return

    direction = "easier" if callback.data == CB_WORKOUT_EASIER else "harder"
    previous_workout = memory_store.get_current_workout(user_id)
    profile = memory_store.get_profile(user_id)

    if not previous_workout or not profile:
        await callback.answer("Тренировка не найдена. Запустите /start.", show_alert=True)
        return

    await callback.answer()
    try:
        await callback.message.edit_text("⏳ Обновляю сложность тренировки...")
    except TelegramBadRequest:
        pass

    service = get_openai_service()
    try:
        adjusted_workout = await service.adjust_workout(
            user_profile=profile,
            previous_workout=previous_workout,
            direction=direction,
        )
    except WorkoutGenerationError as exc:
        logger.error(
            "Workout adjustment failed for user_id=%s, direction=%s: %s",
            user_id,
            direction,
            exc,
        )
        can_adjust = memory_store.can_adjust_workout(user_id, MAX_ADJUSTMENTS)
        await callback.message.edit_text(
            "⚠️ Не удалось обновить тренировку после нескольких попыток.\n"
            "Можно выбрать текущую версию или начать заново через /start.\n\n"
            f"{format_workout_message(previous_workout)}",
            reply_markup=workout_actions_keyboard(can_adjust=can_adjust),
        )
        return

    memory_store.increment_adjustments(user_id)
    memory_store.add_generated_workout(user_id, adjusted_workout)
    await _render_workout_message(callback.message, user_id, adjusted_workout)


@router.callback_query(F.data == CB_WORKOUT_CHOOSE)
async def choose_workout(callback: CallbackQuery) -> None:
    """Save selected workout and ask completion question."""

    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    user_id = callback.from_user.id
    selected = memory_store.select_current_workout(user_id)
    if not selected:
        await callback.answer("Нет выбранной тренировки. Нажмите /start.", show_alert=True)
        return

    await callback.answer("Сохранено")
    await callback.message.edit_text(
        _completion_question_text(),
        reply_markup=completion_status_keyboard(),
    )


@router.callback_query(F.data.startswith(CB_COMPLETED_PREFIX))
async def set_completion_status(callback: CallbackQuery) -> None:
    """Store completion flag and branch to feedback keyboards."""

    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    raw_value = (callback.data or "").removeprefix(CB_COMPLETED_PREFIX)
    if raw_value not in {"yes", "no"}:
        await callback.answer("Неизвестный вариант.", show_alert=True)
        return

    completed = raw_value == "yes"
    memory_store.set_completion_status(callback.from_user.id, completed)
    await callback.answer()

    if completed:
        await callback.message.edit_text(
            "Как прошла тренировка по ощущениям?",
            reply_markup=perceived_difficulty_keyboard(),
        )
        return

    await callback.message.edit_text(
        "Что помешало выполнить тренировку?",
        reply_markup=skip_reason_keyboard(),
    )


@router.callback_query(F.data.startswith(CB_FEEL_PREFIX))
async def set_perceived_difficulty(callback: CallbackQuery) -> None:
    """Store perceived difficulty feedback and finish session."""

    raw_value = (callback.data or "").removeprefix(CB_FEEL_PREFIX)
    if raw_value not in PERCEIVED_DIFFICULTY_OPTIONS:
        await callback.answer("Неизвестный вариант.", show_alert=True)
        return

    user_id = callback.from_user.id
    memory_store.set_perceived_difficulty(user_id, PERCEIVED_DIFFICULTY_OPTIONS[raw_value])
    memory_store.finalize_session(user_id)
    await callback.answer()

    if isinstance(callback.message, Message):
        await callback.message.edit_text("Отличная работа! До следующей тренировки 💪")


@router.callback_query(F.data.startswith(CB_REASON_PREFIX))
async def set_skip_reason(callback: CallbackQuery) -> None:
    """Store skip reason feedback and finish session."""

    raw_value = (callback.data or "").removeprefix(CB_REASON_PREFIX)
    if raw_value not in SKIP_REASON_OPTIONS:
        await callback.answer("Неизвестный вариант.", show_alert=True)
        return

    user_id = callback.from_user.id
    memory_store.set_skip_reason(user_id, SKIP_REASON_OPTIONS[raw_value])
    memory_store.finalize_session(user_id)
    await callback.answer()

    if isinstance(callback.message, Message):
        await callback.message.edit_text("Ничего страшного, в следующий раз получится 🙌")
