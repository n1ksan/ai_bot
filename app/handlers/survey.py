"""Survey FSM handlers for collecting user profile fields."""

from __future__ import annotations

from typing import Any

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.handlers.workout import generate_and_render_initial_workout
from app.keyboards.survey_kb import (
    CB_BACK_TO_DISTANCE,
    CB_BACK_TO_LEVEL,
    CB_BACK_TO_START,
    CB_BACK_TO_STYLES,
    CB_DISTANCE_PREFIX,
    CB_EQUIPMENT_DISABLED,
    CB_EQUIPMENT_DONE,
    CB_EQUIPMENT_PREFIX,
    CB_LEVEL_PREFIX,
    CB_START_SURVEY,
    CB_STYLE_DONE,
    CB_STYLE_PREFIX,
    DISTANCE_CANT_SWIM_DEFAULT_KEY,
    DISTANCE_OPTIONS,
    DISTANCE_SURVEY_KEYS,
    EQUIPMENT_OPTIONS,
    LEVEL_OPTIONS,
    STYLE_OPTIONS,
    distance_keyboard,
    equipment_keyboard,
    level_keyboard,
    selected_labels,
    start_survey_keyboard,
    styles_keyboard,
)
from app.states.survey_states import SurveyStates
from app.storage.memory import memory_store

router = Router()


def _extract_option_key(raw_data: str, prefix: str) -> str:
    """Extract the option key from callback data by prefix."""

    return raw_data.removeprefix(prefix).strip()


def _level_step_text() -> str:
    """Return Step 1 text."""

    return "📋 Шаг 1 из 4\nВыберите ваш уровень плавания:"


def _styles_step_text(selected_count: int) -> str:
    """Return Step 2 text with selected styles counter."""

    return (
        "🏊 Шаг 2 из 4\n"
        "Выберите стили, которыми вы владеете.\n"
        "Можно выбрать несколько вариантов, затем нажмите «✅ Готово».\n"
        f"Выбрано стилей: {selected_count}"
    )


def _distance_step_text() -> str:
    """Return Step 3 text."""

    return "📏 Шаг 3 из 4\nВыберите желаемую дистанцию за тренировку:"


def _equipment_step_text(selected_count: int, short_flow: bool) -> str:
    """Return equipment step text with dynamic numbering."""

    step_title = "🧰 Шаг 2 из 2" if short_flow else "🧰 Шаг 4 из 4"
    return (
        f"{step_title}\n"
        "Выберите доступное оборудование.\n"
        "Можно выбрать несколько вариантов, затем нажмите «✅ Готово».\n"
        f"Выбрано вариантов: {selected_count}"
    )


def _welcome_text() -> str:
    """Return welcome text used for survey reset navigation."""

    return (
        "🏊 Привет! Я ваш ИИ-тренер по плаванию.\n\n"
        "За 4 коротких шага соберу профиль и подготовлю персональную тренировку.\n"
        "Нажмите кнопку ниже, чтобы начать опрос."
    )


async def _safe_edit_message(
    callback: CallbackQuery,
    text: str,
    reply_markup: Any | None = None,
) -> Message | None:
    """Safely edit callback message and fallback to sending a new one."""

    if not isinstance(callback.message, Message):
        return None

    try:
        return await callback.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest:
        return await callback.message.answer(text, reply_markup=reply_markup)


def _build_profile_from_fsm(data: dict[str, Any]) -> dict[str, Any]:
    """Convert FSM survey values into a clean user profile dictionary."""

    level_key = str(data["level"])
    styles_keys = list(data.get("styles", []))
    if level_key == "cant_swim":
        distance_key = DISTANCE_CANT_SWIM_DEFAULT_KEY
    else:
        distance_key = str(data["distance"])
    equipment_keys = list(data.get("equipment", []))

    profile = {
        "level": LEVEL_OPTIONS[level_key],
        "styles": selected_labels(styles_keys, STYLE_OPTIONS),
        "distance_per_session": DISTANCE_OPTIONS.get(
            distance_key,
            DISTANCE_OPTIONS[DISTANCE_CANT_SWIM_DEFAULT_KEY],
        ),
        "equipment": selected_labels(equipment_keys, EQUIPMENT_OPTIONS),
    }
    return profile


def _extract_selected_styles_from_markup(callback: CallbackQuery) -> list[str]:
    """Recover selected styles from current inline keyboard as a fallback."""

    if not isinstance(callback.message, Message) or not callback.message.reply_markup:
        return []

    selected_labels_from_markup: list[str] = []
    for row in callback.message.reply_markup.inline_keyboard:
        for button in row:
            text = (button.text or "").strip()
            if text.startswith("✅ "):
                selected_labels_from_markup.append(text.removeprefix("✅ ").strip())

    selected_keys: list[str] = []
    for key, label in STYLE_OPTIONS.items():
        if label in selected_labels_from_markup:
            selected_keys.append(key)
    return selected_keys


@router.callback_query(F.data == CB_START_SURVEY)
async def start_survey(callback: CallbackQuery, state: FSMContext) -> None:
    """Start a new survey session from the welcome button."""

    await callback.answer()
    user_id = callback.from_user.id

    memory_store.reset_session(user_id)
    await state.clear()
    await state.set_state(SurveyStates.level)

    await _safe_edit_message(
        callback,
        _level_step_text(),
        reply_markup=level_keyboard(),
    )


@router.callback_query(F.data == CB_BACK_TO_START)
async def back_to_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Return user to the welcome screen from survey steps."""

    await callback.answer()
    memory_store.reset_session(callback.from_user.id)
    await state.clear()
    await _safe_edit_message(
        callback,
        _welcome_text(),
        reply_markup=start_survey_keyboard(),
    )


@router.callback_query(F.data == CB_BACK_TO_LEVEL)
async def back_to_level(callback: CallbackQuery, state: FSMContext) -> None:
    """Go back to step 1 (swimming level)."""

    await callback.answer()
    await state.set_state(SurveyStates.level)
    await _safe_edit_message(
        callback,
        _level_step_text(),
        reply_markup=level_keyboard(),
    )


@router.callback_query(F.data == CB_BACK_TO_STYLES)
async def back_to_styles(callback: CallbackQuery, state: FSMContext) -> None:
    """Go back to step 2 (styles) when available."""

    await callback.answer()
    data = await state.get_data()

    if data.get("level") == "cant_swim":
        await state.set_state(SurveyStates.level)
        await _safe_edit_message(
            callback,
            _level_step_text(),
            reply_markup=level_keyboard(),
        )
        return

    selected = set(data.get("styles", []))
    await state.set_state(SurveyStates.styles)
    await _safe_edit_message(
        callback,
        _styles_step_text(len(selected)),
        reply_markup=styles_keyboard(selected),
    )


@router.callback_query(F.data == CB_BACK_TO_DISTANCE)
async def back_to_distance(callback: CallbackQuery, state: FSMContext) -> None:
    """Go back to distance step for regular flow."""

    await callback.answer()
    data = await state.get_data()

    if data.get("level") == "cant_swim":
        await state.set_state(SurveyStates.level)
        await _safe_edit_message(
            callback,
            _level_step_text(),
            reply_markup=level_keyboard(),
        )
        return

    await state.set_state(SurveyStates.distance)
    await _safe_edit_message(
        callback,
        _distance_step_text(),
        reply_markup=distance_keyboard(CB_BACK_TO_STYLES),
    )


@router.callback_query(F.data.startswith(CB_LEVEL_PREFIX))
async def select_level(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle level selection and move to the next required step."""

    key = _extract_option_key(callback.data or "", CB_LEVEL_PREFIX)
    if key not in LEVEL_OPTIONS:
        await callback.answer("Неизвестный вариант уровня.", show_alert=True)
        return

    await callback.answer()
    await state.update_data(level=key, styles=[], equipment=[])

    if key == "cant_swim":
        await state.update_data(distance=DISTANCE_CANT_SWIM_DEFAULT_KEY)
        await state.set_state(SurveyStates.equipment)
        await _safe_edit_message(
            callback,
            _equipment_step_text(0, short_flow=True),
            reply_markup=equipment_keyboard(set(), CB_BACK_TO_LEVEL),
        )
        return

    await state.update_data(distance=None)
    await state.set_state(SurveyStates.styles)
    await _safe_edit_message(
        callback,
        _styles_step_text(0),
        reply_markup=styles_keyboard(set()),
    )


@router.callback_query(F.data.startswith(CB_STYLE_PREFIX))
async def toggle_style(callback: CallbackQuery, state: FSMContext) -> None:
    """Toggle multi-select style options."""

    key = _extract_option_key(callback.data or "", CB_STYLE_PREFIX)
    if key not in STYLE_OPTIONS:
        await callback.answer("Неизвестный стиль.", show_alert=True)
        return

    data = await state.get_data()
    if data.get("level") == "cant_swim":
        await callback.answer()
        return

    selected = set(data.get("styles", []))
    if key in selected:
        selected.remove(key)
    else:
        selected.add(key)

    ordered = [option_key for option_key in STYLE_OPTIONS if option_key in selected]
    await state.set_state(SurveyStates.styles)
    await state.update_data(styles=ordered)
    await callback.answer()

    await _safe_edit_message(
        callback,
        _styles_step_text(len(ordered)),
        reply_markup=styles_keyboard(set(ordered)),
    )


@router.callback_query(F.data == CB_STYLE_DONE)
async def finish_styles(callback: CallbackQuery, state: FSMContext) -> None:
    """Validate style selection and move to distance step."""

    data = await state.get_data()
    selected = list(data.get("styles", []))
    if not selected:
        selected = _extract_selected_styles_from_markup(callback)
        if selected:
            await state.update_data(styles=selected)

    if not selected:
        await callback.answer("Выберите хотя бы один стиль.", show_alert=True)
        return

    await callback.answer()
    await state.set_state(SurveyStates.distance)
    await _safe_edit_message(
        callback,
        _distance_step_text(),
        reply_markup=distance_keyboard(CB_BACK_TO_STYLES),
    )


@router.callback_query(F.data.startswith(CB_DISTANCE_PREFIX))
async def select_distance(callback: CallbackQuery, state: FSMContext) -> None:
    """Handle distance selection and move to equipment step."""

    key = _extract_option_key(callback.data or "", CB_DISTANCE_PREFIX)
    if key not in DISTANCE_SURVEY_KEYS:
        await callback.answer("Неизвестный вариант дистанции.", show_alert=True)
        return

    await callback.answer()
    await state.update_data(distance=key, equipment=[])
    await state.set_state(SurveyStates.equipment)

    await _safe_edit_message(
        callback,
        _equipment_step_text(0, short_flow=False),
        reply_markup=equipment_keyboard(set(), CB_BACK_TO_DISTANCE),
    )


@router.callback_query(F.data.startswith(CB_EQUIPMENT_PREFIX))
async def toggle_equipment(callback: CallbackQuery, state: FSMContext) -> None:
    """Toggle equipment options with special handling for 'No equipment'."""

    key = _extract_option_key(callback.data or "", CB_EQUIPMENT_PREFIX)
    if key not in EQUIPMENT_OPTIONS:
        await callback.answer("Неизвестный вариант оборудования.", show_alert=True)
        return

    data = await state.get_data()
    selected = set(data.get("equipment", []))

    if key == "none":
        if "none" in selected:
            selected.remove("none")
        else:
            selected = {"none"}
    else:
        if "none" in selected:
            await callback.answer()
            return
        if key in selected:
            selected.remove(key)
        else:
            selected.add(key)

    ordered = [option_key for option_key in EQUIPMENT_OPTIONS if option_key in selected]
    await state.set_state(SurveyStates.equipment)
    await state.update_data(equipment=ordered)
    await callback.answer()

    short_flow = data.get("level") == "cant_swim"
    await _safe_edit_message(
        callback,
        _equipment_step_text(len(ordered), short_flow=short_flow),
        reply_markup=equipment_keyboard(
            set(ordered),
            CB_BACK_TO_LEVEL if short_flow else CB_BACK_TO_DISTANCE,
        ),
    )


@router.callback_query(F.data == CB_EQUIPMENT_DISABLED)
async def equipment_disabled(callback: CallbackQuery) -> None:
    """No-op callback for locked equipment options."""

    await callback.answer()


@router.callback_query(F.data == CB_EQUIPMENT_DONE)
async def finish_equipment(callback: CallbackQuery, state: FSMContext) -> None:
    """Validate final survey step, save profile, and generate workout."""

    data = await state.get_data()
    selected = data.get("equipment", [])
    if not selected:
        await callback.answer(
            "Выберите хотя бы один вариант (включая «Без оборудования»).",
            show_alert=True,
        )
        return

    level = data.get("level")
    if level not in LEVEL_OPTIONS:
        await callback.answer(
            "Опрос был прерван. Запустите заново через /start.",
            show_alert=True,
        )
        await state.clear()
        return

    if level == "cant_swim":
        await state.update_data(distance=DISTANCE_CANT_SWIM_DEFAULT_KEY, styles=[])
        data["distance"] = DISTANCE_CANT_SWIM_DEFAULT_KEY
        data["styles"] = []
    elif data.get("distance") not in DISTANCE_SURVEY_KEYS:
        await callback.answer(
            "Опрос был прерван. Запустите заново через /start.",
            show_alert=True,
        )
        await state.clear()
        return

    await callback.answer()
    profile = _build_profile_from_fsm(data)
    user_id = callback.from_user.id
    memory_store.save_profile(user_id, profile)
    await state.clear()

    generating_message = await _safe_edit_message(
        callback,
        "⏳ Составляю персональную тренировку...",
    )
    if generating_message is None:
        return

    await generate_and_render_initial_workout(generating_message, user_id)
