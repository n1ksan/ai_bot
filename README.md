# AI Swimming Coach Telegram Bot

MVP Telegram bot that runs a short onboarding survey and generates a personalized swimming workout via OpenAI Structured Output (`response_format: json_schema`).

## Features

- FSM-driven 4-step survey with `aiogram` 3.x.
- Separate data layers:
  - `FSMContext` for survey steps only.
  - Dedicated in-memory repository (`app/storage/memory.py`) for profiles, generated workouts, and history.
- Structured OpenAI workout generation with strict JSON schema validation.
- Workout item structure in every section:
  - `task` (Задание)
  - `how_to_swim` (Как плыть)
  - `intensity` (Интенсивность)
  - `rest` (Отдых)
- Workout difficulty adjustments (`easier` / `harder`) with session limit (3 max).
- Workout selection and post-workout feedback flow.
- Russian-first UI/UX for all user-visible Telegram messages and buttons.
- Modular architecture ready for future DB/dashboard/adaptive logic/Mini App.

## Environment Variables

- `BOT_TOKEN`: Telegram bot token from BotFather.
- `OPENAI_API_KEY`: OpenAI API key.
- `OPENAI_MODEL`: Model name (default example: `gpt-5.4`).
- `LOG_LEVEL`: Python logging level (`INFO`, `DEBUG`, etc.).

## Project Structure

```text
swimming_bot/
|-- app/
|   |-- bot.py
|   |-- config.py
|   |-- handlers/
|   |   |-- __init__.py
|   |   |-- start.py
|   |   |-- survey.py
|   |   `-- workout.py
|   |-- keyboards/
|   |   |-- __init__.py
|   |   |-- survey_kb.py
|   |   `-- workout_kb.py
|   |-- services/
|   |   |-- __init__.py
|   |   `-- openai_service.py
|   |-- states/
|   |   |-- __init__.py
|   |   `-- survey_states.py
|   |-- storage/
|   |   |-- __init__.py
|   |   `-- memory.py
|   `-- utils/
|       |-- __init__.py
|       |-- formatters.py
|       `-- prompts.py
|-- requirements.txt
|-- .env.example
`-- README.md
```

## Run Instructions

1. Clone the repository and open the project:
   - `git clone <your-repo-url>`
   - `cd swimming_bot`
2. Create and activate a virtual environment:
   - Windows PowerShell:
     - `python -m venv .venv`
     - `.venv\Scripts\Activate.ps1`
   - macOS/Linux:
     - `python -m venv .venv`
     - `source .venv/bin/activate`
3. Install dependencies:
   - `pip install -r requirements.txt`
4. Configure environment:
   - `copy .env.example .env` (Windows) or `cp .env.example .env` (macOS/Linux)
   - Fill in `BOT_TOKEN` and `OPENAI_API_KEY`.
5. Start the bot:
   - `python -m app.bot`

## Notes

- If OpenAI returns invalid or empty JSON, the bot retries up to 3 times.
- After 3 failed attempts, the user gets a restart suggestion (`/start`).
- This MVP uses in-memory storage, so data resets when the process restarts.
