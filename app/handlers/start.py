"""Start command and welcome interactions."""

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards.survey_kb import start_survey_keyboard
from app.storage.memory import memory_store

router = Router()


def build_welcome_text() -> str:
    """Return welcome message text for /start and back navigation."""

    return (
        "🏊 Привет! Я ваш ИИ-тренер по плаванию.\n\n"
        "За 4 коротких шага соберу профиль и подготовлю персональную тренировку.\n"
        "Нажмите кнопку ниже, чтобы начать опрос."
    )


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Handle /start command and offer survey launch button."""

    await state.clear()
    memory_store.reset_session(message.from_user.id)
    await message.answer(build_welcome_text(), reply_markup=start_survey_keyboard())
