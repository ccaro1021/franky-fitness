# Franky Fitness — CLAUDE.md

## What This Project Is

Franky Fitness is a multi-agent meal planning, exercise, and grocery assistant built for a couple. It uses the Anthropic Python SDK to power a conversational AI agent (Franky) that helps plan meals, suggest workouts, and generate grocery lists tailored to two people's preferences and goals.

The long-term vision is a set of specialized agents — one for nutrition, one for grocery planning, one for exercise — that can coordinate and be invoked through a single conversation interface.

## Who It's For

**Chris and Kaitlyn.** Both partners' needs, preferences, and dietary restrictions should always be considered. Features should be designed for two people, not one.

## Tech Stack

- **Language:** Python 3.13
- **AI SDK:** Anthropic Python SDK (`anthropic`)
- **Data modeling:** Pydantic (`BaseModel` for structured outputs like meals, grocery lists)
- **Environment:** `python-dotenv` for loading `.env`; `venv` for package isolation
- **Recipe data:** Spoonacular Food API — provides recipes, nutritional metadata, and structured ingredient lists
- **API keys:** Stored in `.env` as `ANTHROPIC_API_KEY` and `SPOONACULAR_API_KEY` — never hardcode them

## Project Structure

```
franky-fitness/
├── .env                  # API keys (gitignored)
├── .gitignore
├── CLAUDE.md             # This file
├── README.md
├── requirements.txt      # Direct dependencies
├── models.py             # Pydantic models: Person, Meal, Ingredient, WeeklyPlan, etc.
├── spoonacular.py        # Spoonacular API client — search_recipes(), get_recipe()
├── system_prompt.txt     # Franky's identity, goals, capabilities, and constraints
├── franky.py             # Main chatbot loop (work in progress)
├── hello_claude.py       # First API proof-of-concept (throwaway)
├── phase-0-notes.md      # Learning journal
└── venv/                 # Virtual environment (gitignored)
```

## Current Phase: Phase 0 — Foundations

We are in Phase 0. The goal is to get comfortable with Python, the Anthropic SDK, and basic agent patterns before building real features.

**Phase 0 checklist:**
- [x] Set up venv and install dependencies
- [x] Make a successful API call (`hello_claude.py`)
- [x] Build a multi-turn conversation loop with history (`franky.py`)
- [x] Understand .env secrets pattern
- [x] Add a system prompt to give Franky a personality and fitness context
- [x] Fix indentation bug in `franky.py` (line 15)
- [x] Guard `main()` with `if __name__ == "__main__":`
- [ ] Connect the `Meal` Pydantic model to the actual chat flow

**Phase 1 (next):** Tool use, structured outputs, and the first real feature (meal planning).

## Coding Conventions

### General
- Keep files small and single-purpose. One agent or feature per file.
- Use `if __name__ == "__main__":` to guard entry points — never call `main()` at module level.
- Load environment variables with `load_dotenv()` at the top of every script that needs the API.

### Anthropic SDK
- Always pass `conversation_history` in API calls to maintain multi-turn context.
- Always set a `system` prompt — never leave Franky without an identity and instructions.
- Default model: `claude-sonnet-4-6` unless there's a reason to change.
- Always set `max_tokens` explicitly.
- Wrap API calls in try/except for at minimum `anthropic.AuthenticationError` and `anthropic.RateLimitError`.

### Pydantic
- Use `BaseModel` for any structured data returned from the model (meals, grocery lists, workout plans).
- Define models in a dedicated `models.py` file once there are more than one or two.

### Naming
- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Files: `snake_case.py`

### What to Avoid
- Don't hardcode API keys, user preferences, or meal data.
- Don't add features before the current phase checklist is complete.
- Don't skip error handling on API calls.
