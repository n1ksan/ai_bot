"""Dedicated in-memory storage for profiles, workouts, and session history."""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from typing import Any, TypedDict


class WorkoutItem(TypedDict):
    """One exercise item in a section of the workout."""

    task: str
    how_to_swim: str
    intensity: str
    rest: str


class WorkoutPlan(TypedDict):
    """Typed shape of the workout payload stored in memory."""

    warmup: list[WorkoutItem]
    technique: list[WorkoutItem]
    main_set: list[WorkoutItem]
    cooldown: list[WorkoutItem]


class InMemoryUserStore:
    """Simple repository-like store keyed by Telegram user ID."""

    def __init__(self) -> None:
        """Initialize internal memory dictionary."""

        self._users: dict[int, dict[str, Any]] = {}

    @staticmethod
    def _new_session() -> dict[str, Any]:
        return {
            "generated_workouts": [],
            "current_workout": None,
            "selected_workout": None,
            "selected_at_utc": None,
            "adjustments_used": 0,
            "completion": {
                "completed": None,
                "perceived_difficulty": None,
                "skip_reason": None,
            },
        }

    @staticmethod
    def _new_user_record() -> dict[str, Any]:
        return {
            "profile": {},
            "session": InMemoryUserStore._new_session(),
            "history": [],
        }

    def _get_or_create_user(self, user_id: int) -> dict[str, Any]:
        if user_id not in self._users:
            self._users[user_id] = self._new_user_record()
        return self._users[user_id]

    def reset_session(self, user_id: int) -> None:
        """Reset only the active session data for a user."""

        user = self._get_or_create_user(user_id)
        user["session"] = self._new_session()

    def save_profile(self, user_id: int, profile: dict[str, Any]) -> None:
        """Persist current survey profile for a user."""

        user = self._get_or_create_user(user_id)
        user["profile"] = copy.deepcopy(profile)

    def get_profile(self, user_id: int) -> dict[str, Any]:
        """Return a copy of user profile data."""

        user = self._get_or_create_user(user_id)
        return copy.deepcopy(user["profile"])

    def add_generated_workout(self, user_id: int, workout: WorkoutPlan) -> None:
        """Store a generated workout as current and append to session history."""

        user = self._get_or_create_user(user_id)
        workout_copy = copy.deepcopy(workout)
        session = user["session"]
        session["generated_workouts"].append(workout_copy)
        session["current_workout"] = workout_copy

    def get_current_workout(self, user_id: int) -> WorkoutPlan | None:
        """Return the currently displayed workout."""

        user = self._get_or_create_user(user_id)
        workout = user["session"]["current_workout"]
        return copy.deepcopy(workout) if workout else None

    def get_adjustments_used(self, user_id: int) -> int:
        """Return the number of difficulty adjustments in this session."""

        user = self._get_or_create_user(user_id)
        return int(user["session"]["adjustments_used"])

    def increment_adjustments(self, user_id: int) -> int:
        """Increase adjustment counter and return the new value."""

        user = self._get_or_create_user(user_id)
        user["session"]["adjustments_used"] += 1
        return int(user["session"]["adjustments_used"])

    def can_adjust_workout(self, user_id: int, max_adjustments: int) -> bool:
        """Check if the user can still request difficulty adjustments."""

        return self.get_adjustments_used(user_id) < max_adjustments

    def select_current_workout(self, user_id: int) -> bool:
        """Mark current workout as selected for this session."""

        user = self._get_or_create_user(user_id)
        current = user["session"]["current_workout"]
        if not current:
            return False

        user["session"]["selected_workout"] = copy.deepcopy(current)
        user["session"]["selected_at_utc"] = datetime.now(UTC).isoformat()
        return True

    def set_completion_status(self, user_id: int, completed: bool) -> None:
        """Store completion boolean and mirror it in the profile."""

        user = self._get_or_create_user(user_id)
        user["session"]["completion"]["completed"] = completed
        user["profile"]["last_workout_completed"] = completed

    def set_perceived_difficulty(self, user_id: int, difficulty: str) -> None:
        """Store perceived difficulty feedback in session and profile."""

        user = self._get_or_create_user(user_id)
        user["session"]["completion"]["perceived_difficulty"] = difficulty
        user["profile"]["last_perceived_difficulty"] = difficulty

    def set_skip_reason(self, user_id: int, reason: str) -> None:
        """Store skip reason feedback in session and profile."""

        user = self._get_or_create_user(user_id)
        user["session"]["completion"]["skip_reason"] = reason
        user["profile"]["last_skip_reason"] = reason

    def finalize_session(self, user_id: int) -> None:
        """Append final session snapshot to user history."""

        user = self._get_or_create_user(user_id)
        session = user["session"]
        selected_workout = session["selected_workout"]
        if not selected_workout:
            return

        snapshot = {
            "created_at_utc": datetime.now(UTC).isoformat(),
            "profile": copy.deepcopy(user["profile"]),
            "selected_workout": copy.deepcopy(selected_workout),
            "completion": copy.deepcopy(session["completion"]),
            "adjustments_used": session["adjustments_used"],
            "generated_workouts_count": len(session["generated_workouts"]),
        }
        user["history"].append(snapshot)

    def get_history(self, user_id: int) -> list[dict[str, Any]]:
        """Return session history snapshots for the user."""

        user = self._get_or_create_user(user_id)
        return copy.deepcopy(user["history"])


memory_store = InMemoryUserStore()
