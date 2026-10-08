"""Routers package for bot handlers."""

from app.handlers.start import router as start_router
from app.handlers.survey import router as survey_router
from app.handlers.workout import router as workout_router

__all__ = ("start_router", "survey_router", "workout_router")

