"""OpenAI integration for structured swimming workout generation."""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from typing import Any, Callable, Final, TypedDict

from openai import AsyncOpenAI

from app.config import get_settings
from app.utils.prompts import (
    SYSTEM_PROMPT,
    build_adjustment_user_prompt,
    build_generation_user_prompt,
)

logger = logging.getLogger(__name__)

EXPECTED_WORKOUT_KEYS: Final[set[str]] = {
    "warmup",
    "technique",
    "main_set",
    "cooldown",
}

EXPECTED_ITEM_KEYS: Final[set[str]] = {
    "task",
    "how_to_swim",
    "intensity",
    "rest",
}

MULTIPLIER_DISTANCE_RE: Final[re.Pattern[str]] = re.compile(
    r"(?P<reps>\d+(?:[.,]\d+)?)\s*[xX×хХ]\s*(?P<distance>\d+(?:[.,]\d+)?)\s*(?:m|м|meters?|метр(?:а|ов)?)\b",
    flags=re.IGNORECASE,
)
SINGLE_DISTANCE_RE: Final[re.Pattern[str]] = re.compile(
    r"(?P<distance>\d+(?:[.,]\d+)?)\s*(?:m|м|meters?|метр(?:а|ов)?)\b",
    flags=re.IGNORECASE,
)

WORKOUT_ITEM_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "task": {"type": "string", "minLength": 1},
        "how_to_swim": {"type": "string", "minLength": 1},
        "intensity": {"type": "string", "minLength": 1},
        "rest": {"type": "string", "minLength": 1},
    },
    "required": ["task", "how_to_swim", "intensity", "rest"],
    "additionalProperties": False,
}

WORKOUT_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "warmup": {
            "type": "array",
            "minItems": 2,
            "items": WORKOUT_ITEM_SCHEMA,
        },
        "technique": {
            "type": "array",
            "minItems": 2,
            "items": WORKOUT_ITEM_SCHEMA,
        },
        "main_set": {
            "type": "array",
            "minItems": 2,
            "items": WORKOUT_ITEM_SCHEMA,
        },
        "cooldown": {
            "type": "array",
            "minItems": 2,
            "items": WORKOUT_ITEM_SCHEMA,
        },
    },
    "required": ["warmup", "technique", "main_set", "cooldown"],
    "additionalProperties": False,
}


class WorkoutItem(TypedDict):
    """One workout item with execution details."""

    task: str
    how_to_swim: str
    intensity: str
    rest: str


class WorkoutPlan(TypedDict):
    """Structured workout payload returned by OpenAI."""

    warmup: list[WorkoutItem]
    technique: list[WorkoutItem]
    main_set: list[WorkoutItem]
    cooldown: list[WorkoutItem]


class WorkoutGenerationError(RuntimeError):
    """Raised when workout generation fails after all retry attempts."""


class OpenAIService:
    """Encapsulates OpenAI requests and structured response parsing."""

    def __init__(self, api_key: str, model: str, max_retries: int = 3) -> None:
        """Initialize OpenAI client and model settings."""

        self._client = AsyncOpenAI(api_key=api_key)
        self._max_retries = max_retries
        self._model = model

    async def generate_workout(self, user_profile: dict[str, Any]) -> WorkoutPlan:
        """Generate a new workout from user profile data."""

        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_generation_user_prompt(user_profile),
            },
        ]
        return await self._request_with_retries(messages)

    async def adjust_workout(
        self,
        user_profile: dict[str, Any],
        previous_workout: WorkoutPlan,
        direction: str,
    ) -> WorkoutPlan:
        """Generate an easier/harder variant from previous workout."""

        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_adjustment_user_prompt(
                    user_profile=user_profile,
                    previous_workout=previous_workout,
                    direction=direction,
                ),
            },
        ]
        previous_total = self._workout_total_meters(previous_workout)
        validator = self._build_adjustment_validator(direction, previous_total)
        return await self._request_with_retries(messages, validator=validator)

    async def _request_with_retries(
        self,
        messages: list[dict[str, str]],
        validator: Callable[[WorkoutPlan], bool] | None = None,
    ) -> WorkoutPlan:
        """Request workout JSON from OpenAI with retries."""

        last_error = "unknown error"

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self._request_structured_output(messages)
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                logger.exception(
                    "OpenAI request failed on attempt %s/%s with model=%s. Error=%s",
                    attempt,
                    self._max_retries,
                    self._model,
                    last_error,
                )
                continue

            workout = self._extract_workout(response)
            if workout is not None:
                if validator and not validator(workout):
                    last_error = "workout failed adjustment bounds validation"
                    logger.error(
                        "OpenAI workout failed post-validation on attempt %s/%s with model=%s.",
                        attempt,
                        self._max_retries,
                        self._model,
                    )
                    continue

                return workout

            last_error = "invalid or empty JSON returned"
            logger.error(
                "OpenAI returned invalid workout JSON on attempt %s/%s with model=%s.",
                attempt,
                self._max_retries,
                self._model,
            )

        raise WorkoutGenerationError(
            "Failed to generate valid workout after maximum retry attempts. "
            f"Last error: {last_error}"
        )

    async def _request_structured_output(self, messages: list[dict[str, str]]) -> Any:
        """Request structured output; prefer Chat Completions, fallback to Responses."""

        try:
            return await self._client.chat.completions.create(
                model=self._model,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "workout",
                        "strict": True,
                        "schema": WORKOUT_SCHEMA,
                    },
                },
                messages=messages,
            )
        except Exception as chat_exc:
            logger.warning(
                "Chat Completions structured output failed for model=%s, fallback to Responses API. Error=%s: %s",
                self._model,
                type(chat_exc).__name__,
                chat_exc,
            )

            # Keep the same model, but use Responses API text.format json_schema.
            return await self._client.responses.create(
                model=self._model,
                input=messages,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "workout",
                        "strict": True,
                        "schema": WORKOUT_SCHEMA,
                    }
                },
            )

    @staticmethod
    def _parse_number(raw_value: str) -> float:
        """Parse numeric string with dot/comma decimal separator."""

        return float(raw_value.replace(",", "."))

    def _distance_from_task_text(self, task_text: str) -> int:
        """Extract distance in meters from one task text."""

        if not task_text.strip():
            return 0

        total = 0.0
        covered_spans: list[tuple[int, int]] = []

        for match in MULTIPLIER_DISTANCE_RE.finditer(task_text):
            reps = self._parse_number(match.group("reps"))
            distance = self._parse_number(match.group("distance"))
            total += reps * distance
            covered_spans.append(match.span())

        if covered_spans:
            fragments: list[str] = []
            cursor = 0
            for start, end in sorted(covered_spans):
                if cursor < start:
                    fragments.append(task_text[cursor:start])
                cursor = max(cursor, end)
            if cursor < len(task_text):
                fragments.append(task_text[cursor:])
            remainder = " ".join(fragments)
        else:
            remainder = task_text

        for match in SINGLE_DISTANCE_RE.finditer(remainder):
            total += self._parse_number(match.group("distance"))

        return int(round(total))

    def _workout_total_meters(self, workout: WorkoutPlan) -> int:
        """Calculate total meters for a workout from all task fields."""

        total = 0
        for section in EXPECTED_WORKOUT_KEYS:
            items = workout.get(section, [])
            for item in items:
                task_text = item.get("task", "")
                total += self._distance_from_task_text(task_text)
        return total

    def _build_adjustment_validator(
        self,
        direction: str,
        previous_total: int,
    ) -> Callable[[WorkoutPlan], bool]:
        """Return validator that enforces small difficulty changes."""

        def _validator(candidate: WorkoutPlan) -> bool:
            if previous_total <= 0:
                return True

            current_total = self._workout_total_meters(candidate)
            if current_total <= 0:
                logger.error("Adjusted workout has non-positive total meters.")
                return False

            min_delta = max(25, int(round(previous_total * 0.05)))
            max_delta = max(50, int(round(previous_total * 0.20)))
            delta = current_total - previous_total

            if direction == "easier":
                is_valid = -max_delta <= delta <= -min_delta
            else:
                is_valid = min_delta <= delta <= max_delta

            if not is_valid:
                logger.error(
                    "Adjusted workout delta out of range: previous=%s, current=%s, delta=%s, direction=%s",
                    previous_total,
                    current_total,
                    delta,
                    direction,
                )
            return is_valid

        return _validator

    def _extract_workout(self, response: Any) -> WorkoutPlan | None:
        """Parse and validate the workout response payload."""

        content = self._extract_text_content(response)

        if not content:
            logger.error("OpenAI returned an empty response body.")
            return None

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse OpenAI JSON response: %s", exc)
            return None

        if not self._is_valid_workout(payload):
            logger.error("OpenAI JSON does not match expected workout structure.")
            return None

        return payload

    def _extract_text_content(self, response: Any) -> str:
        """Extract text content from both Chat Completions and Responses API payloads."""

        # Chat Completions style
        choices = getattr(response, "choices", None)
        if choices:
            raw_content = choices[0].message.content
            if isinstance(raw_content, str):
                return raw_content.strip()
            if isinstance(raw_content, list):
                text_parts: list[str] = []
                for part in raw_content:
                    text = getattr(part, "text", None)
                    if isinstance(text, str):
                        text_parts.append(text)
                return "".join(text_parts).strip()

        # Responses API style
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        output = getattr(response, "output", None)
        if isinstance(output, list):
            text_parts: list[str] = []
            for item in output:
                content = getattr(item, "content", None)
                if isinstance(content, list):
                    for part in content:
                        text = getattr(part, "text", None)
                        if isinstance(text, str):
                            text_parts.append(text)
            joined = "".join(text_parts).strip()
            if joined:
                return joined

        return ""

    def _is_valid_workout(self, payload: Any) -> bool:
        """Validate final workout object before returning it."""

        if not isinstance(payload, dict):
            return False

        if set(payload.keys()) != EXPECTED_WORKOUT_KEYS:
            return False

        for key in EXPECTED_WORKOUT_KEYS:
            items = payload.get(key)
            if not isinstance(items, list) or len(items) < 2:
                return False
            for item in items:
                if not isinstance(item, dict):
                    return False
                if set(item.keys()) != EXPECTED_ITEM_KEYS:
                    return False
                if any(
                    not isinstance(item[field], str) or not item[field].strip()
                    for field in EXPECTED_ITEM_KEYS
                ):
                    return False

        return True


@lru_cache(maxsize=1)
def get_openai_service() -> OpenAIService:
    """Return cached OpenAI service singleton."""

    settings = get_settings()
    return OpenAIService(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
    )
