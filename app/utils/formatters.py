"""Helpers for converting workout JSON into Telegram-friendly text."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

_WORKOUT_KEYS: tuple[str, ...] = ("warmup", "technique", "main_set", "cooldown")

_MULTIPLIER_DISTANCE_RE = re.compile(
    r"(?P<reps>\d+(?:[.,]\d+)?)\s*[xX×хХ]\s*(?P<distance>\d+(?:[.,]\d+)?)\s*(?:м|метр(?:а|ов)?)\b",
    flags=re.IGNORECASE,
)
_SINGLE_DISTANCE_RE = re.compile(
    r"(?P<distance>\d+(?:[.,]\d+)?)\s*(?:м|метр(?:а|ов)?)\b",
    flags=re.IGNORECASE,
)


def _value(value: str | None) -> str:
    """Return sanitized display value for nullable strings."""

    if isinstance(value, str) and value.strip():
        return value.strip()
    return "-"


def _parse_number(raw_value: str) -> float:
    """Parse numeric string with dot/comma decimal separator."""

    return float(raw_value.replace(",", "."))


def _distance_from_task_text(task_text: str) -> int:
    """Extract distance in meters from one task text."""

    if not task_text.strip():
        return 0

    total = 0.0
    covered_spans: list[tuple[int, int]] = []

    for match in _MULTIPLIER_DISTANCE_RE.finditer(task_text):
        reps = _parse_number(match.group("reps"))
        distance = _parse_number(match.group("distance"))
        total += reps * distance
        covered_spans.append(match.span())

    if covered_spans:
        leftovers: list[str] = []
        cursor = 0
        for start, end in sorted(covered_spans):
            if cursor < start:
                leftovers.append(task_text[cursor:start])
            cursor = max(cursor, end)
        if cursor < len(task_text):
            leftovers.append(task_text[cursor:])
        remainder = " ".join(leftovers)
    else:
        remainder = task_text

    for match in _SINGLE_DISTANCE_RE.finditer(remainder):
        total += _parse_number(match.group("distance"))

    return int(round(total))


def _calculate_total_meters(workout: Mapping[str, Sequence[Mapping[str, str]]]) -> int:
    """Calculate total workout meters from all task fields."""

    total = 0
    for section_key in _WORKOUT_KEYS:
        for item in workout.get(section_key, []):
            total += _distance_from_task_text(_value(item.get("task")))
    return total


def _format_section(title: str, items: Sequence[Mapping[str, str]]) -> str:
    """Format one workout section as title + detailed tasks."""

    lines: list[str] = [title]
    for index, item in enumerate(items):
        lines.append("")
        lines.append(f"Задание: {_value(item.get('task'))}")
        lines.append(f"Как плыть: {_value(item.get('how_to_swim'))}")
        lines.append(f"Интенсивность: {_value(item.get('intensity'))}")
        lines.append(f"Отдых: {_value(item.get('rest'))}")

        if index < len(items) - 1:
            lines.append("")

    return "\n".join(lines).rstrip()


def format_workout_message(workout: Mapping[str, Sequence[Mapping[str, str]]]) -> str:
    """Build the final formatted Telegram workout message."""

    warmup = _format_section("🔥 РАЗМИНКА", workout.get("warmup", []))
    technique = _format_section("🎯 ТЕХНИКА", workout.get("technique", []))
    main_set = _format_section("💪 ОСНОВНАЯ СЕРИЯ", workout.get("main_set", []))
    cooldown = _format_section("🧘 ЗАМИНКА", workout.get("cooldown", []))
    total_meters = _calculate_total_meters(workout)

    return (
        "🏊 ВАША ТРЕНИРОВКА\n\n"
        f"{warmup}\n\n"
        f"{technique}\n\n"
        f"{main_set}\n\n"
        f"{cooldown}\n\n"
        f"📏 ИТОГО: {total_meters} м"
    )
