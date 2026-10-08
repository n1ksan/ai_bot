"""Inline keyboards used in the survey flow."""

from collections.abc import Iterable

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

CB_START_SURVEY = "survey:start"
CB_LEVEL_PREFIX = "survey:level:"
CB_STYLE_PREFIX = "survey:style:"
CB_STYLE_DONE = "survey:style_done"
CB_DISTANCE_PREFIX = "survey:distance:"
CB_EQUIPMENT_PREFIX = "survey:equipment:"
CB_EQUIPMENT_DONE = "survey:equipment_done"
CB_EQUIPMENT_DISABLED = "survey:equipment_disabled"

CB_BACK_TO_START = "survey:back:start"
CB_BACK_TO_LEVEL = "survey:back:level"
CB_BACK_TO_STYLES = "survey:back:styles"
CB_BACK_TO_DISTANCE = "survey:back:distance"

DISTANCE_CANT_SWIM_DEFAULT_KEY = "cant_swim_default"
DISTANCE_SURVEY_KEYS: tuple[str, ...] = (
    "under_500",
    "500_1000",
    "1000_2000",
    "2000_plus",
)

LEVEL_OPTIONS: dict[str, str] = {
    "cant_swim": "Не умею плавать",
    "beginner": "Начинающий",
    "intermediate": "Средний",
    "advanced": "Продвинутый",
}

STYLE_OPTIONS: dict[str, str] = {
    "freestyle": "Кроль (на груди)",
    "breaststroke": "Брасс",
    "backstroke": "На спине",
    "butterfly": "Баттерфляй",
}

DISTANCE_OPTIONS: dict[str, str] = {
    "under_500": "До 500 м",
    "500_1000": "500-1000 м",
    "1000_2000": "1000-2000 м",
    "2000_plus": "2000+ м",
    DISTANCE_CANT_SWIM_DEFAULT_KEY: "Без фиксированной дистанции (адаптация к воде)",
}

EQUIPMENT_OPTIONS: dict[str, str] = {
    "kickboard": "Доска",
    "pull_buoy": "Калабашка (pull buoy)",
    "paddles": "Лопатки",
    "fins": "Ласты",
    "none": "Без оборудования",
}


def selected_labels(selected_keys: Iterable[str], options: dict[str, str]) -> list[str]:
    """Convert selected option keys to human-readable labels."""

    return [options[key] for key in options if key in selected_keys]


def start_survey_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard with a single survey start button."""

    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Начать опрос", callback_data=CB_START_SURVEY)
    builder.adjust(1)
    return builder.as_markup()


def level_keyboard() -> InlineKeyboardMarkup:
    """Build keyboard for the swimming level step."""

    builder = InlineKeyboardBuilder()
    for key, label in LEVEL_OPTIONS.items():
        builder.button(text=label, callback_data=f"{CB_LEVEL_PREFIX}{key}")
    builder.button(text="🔙 Назад", callback_data=CB_BACK_TO_START)
    builder.adjust(1)
    return builder.as_markup()


def styles_keyboard(selected_styles: set[str]) -> InlineKeyboardMarkup:
    """Build multi-select keyboard for swimming styles."""

    builder = InlineKeyboardBuilder()
    for key, label in STYLE_OPTIONS.items():
        button_text = f"✅ {label}" if key in selected_styles else label
        builder.button(text=button_text, callback_data=f"{CB_STYLE_PREFIX}{key}")

    builder.button(text="✅ Готово", callback_data=CB_STYLE_DONE)
    builder.button(text="🔙 Назад", callback_data=CB_BACK_TO_LEVEL)
    builder.adjust(1)
    return builder.as_markup()


def distance_keyboard(back_callback_data: str) -> InlineKeyboardMarkup:
    """Build keyboard for distance-per-session selection."""

    builder = InlineKeyboardBuilder()
    for key in DISTANCE_SURVEY_KEYS:
        label = DISTANCE_OPTIONS[key]
        builder.button(text=label, callback_data=f"{CB_DISTANCE_PREFIX}{key}")
    builder.button(text="🔙 Назад", callback_data=back_callback_data)
    builder.adjust(1)
    return builder.as_markup()


def equipment_keyboard(
    selected_equipment: set[str],
    back_callback_data: str,
) -> InlineKeyboardMarkup:
    """Build multi-select keyboard for available equipment."""

    builder = InlineKeyboardBuilder()
    no_equipment_selected = "none" in selected_equipment

    for key, label in EQUIPMENT_OPTIONS.items():
        button_text = f"✅ {label}" if key in selected_equipment else label
        callback_data = (
            f"{CB_EQUIPMENT_PREFIX}{key}"
            if key == "none" or not no_equipment_selected
            else CB_EQUIPMENT_DISABLED
        )
        builder.button(text=button_text, callback_data=callback_data)

    builder.button(text="✅ Готово", callback_data=CB_EQUIPMENT_DONE)
    builder.button(text="🔙 Назад", callback_data=back_callback_data)
    builder.adjust(1)
    return builder.as_markup()
