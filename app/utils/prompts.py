"""Prompt templates for OpenAI workout generation."""

from __future__ import annotations

import json
from typing import Any

SYSTEM_PROMPT = """You are a professional swimming coach.
Your task is to return only valid JSON that strictly matches the provided response_format schema.

Hard rules:
1. Return only JSON. No explanations, no markdown, no extra text.
2. Root object must contain exactly 4 keys: warmup, technique, main_set, cooldown.
3. Each section must contain at least 2 items.
4. Each section item must be an object with exactly these fields: task, how_to_swim, intensity, rest.
5. All field values must be non-empty strings.
6. The final workout text content must be in Russian.
7. Do not use equipment that the user does not have.
8. Use only swimming styles from the user's profile.
9. If level is "Не умею плавать", all tasks must be near the wall or in shallow water only.
10. Total workout volume must match the user's selected distance range.
11. If level is "Не умею плавать" and distance is "Без фиксированной дистанции (адаптация к воде)",
    produce a short adaptation-focused session near the wall/shallow water without long-distance requirements.
12. Do not repeat identical exercises across sections.
13. In task, always include meters in a parseable format: "NxM м" or "M м".
14. technique section must be narrowly focused: each exercise targets one specific technical skill.
15. Prefer specialized drills in technique, for example:
    - "6x25 м работа ногами на боку для положения тела в воде"
    - "4x50 м вертушка: 3 гребка кролем + 3 гребка на спине"
    - "4x25 м скольжение и вытяжение после входа руки"
16. For easier/harder requests, adjust load only slightly:
    around 5-15% by total meters and/or by one intensity step, without radical program changes.
"""


def build_generation_user_prompt(user_profile: dict[str, Any]) -> str:
    """Create user prompt for first workout generation."""

    profile_json = json.dumps(user_profile, ensure_ascii=False, indent=2)
    return (
        "Generate a personalized swimming workout based on the user profile below.\n"
        "Critical: return JSON only, with sections warmup/technique/main_set/cooldown.\n"
        "Each item must include task/how_to_swim/intensity/rest.\n"
        "Technique must contain narrow, skill-specific drills.\n"
        "All workout content in fields must be written in Russian.\n\n"
        f"User profile:\n{profile_json}"
    )


def build_adjustment_user_prompt(
    user_profile: dict[str, Any],
    previous_workout: dict[str, list[dict[str, str]]],
    direction: str,
) -> str:
    """Create user prompt for workout difficulty adjustment."""

    if direction not in {"easier", "harder"}:
        raise ValueError("direction must be either 'easier' or 'harder'")

    direction_instruction = (
        "Make the workout slightly easier (not radically): about 5-15% less total distance "
        "and/or one step lower intensity."
        if direction == "easier"
        else "Make the workout slightly harder (not radically): about 5-15% more total distance "
        "and/or one step higher intensity."
    )

    profile_json = json.dumps(user_profile, ensure_ascii=False, indent=2)
    workout_json = json.dumps(previous_workout, ensure_ascii=False, indent=2)

    return (
        "Adjust the difficulty of the previous workout.\n"
        f"{direction_instruction}\n"
        "Keep structure, profile constraints, and overall style.\n"
        "Return JSON only in the same schema.\n"
        "Each section item must include task/how_to_swim/intensity/rest.\n"
        "task must always include explicit distance in meters.\n"
        "All workout content in fields must be in Russian.\n\n"
        f"User profile:\n{profile_json}\n\n"
        f"Previous workout:\n{workout_json}"
    )
