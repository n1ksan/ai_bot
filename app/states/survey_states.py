"""FSM states for the onboarding survey."""

from aiogram.fsm.state import State, StatesGroup


class SurveyStates(StatesGroup):
    """Step-by-step survey states."""

    level = State()
    styles = State()
    distance = State()
    equipment = State()

