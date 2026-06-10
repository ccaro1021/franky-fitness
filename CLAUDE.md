# Franky Fitness — CLAUDE.md

> **Start here:** Read [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) at the start of each session — it holds the architecture decisions, build order, and the running decision log. The full product vision is in [`docs/franky-fitness-prd.md`](docs/franky-fitness-prd.md).

## What This Project Is

Franky Fitness is a multi-agent meal planning, exercise, and grocery assistant built for a couple. It uses the Anthropic Python SDK to power a conversational AI agent (Franky) that helps plan meals, suggest workouts, and generate grocery lists tailored to two people's preferences and goals.

The long-term vision is a set of specialized agents — one for nutrition, one for grocery planning, one for exercise — that can coordinate and be invoked through a single conversation interface.

## Who It's For

**Chris and Kaitlyn.** Both partners' needs, preferences, and dietary restrictions should always be considered. Features should be designed for two people, not one.

## Tech Stack

- **Language:** Python 3.13
- **AI SDK:** Anthropic Python SDK (`anthropic`)
- **Backend:** FastAPI + Uvicorn — serves the chat and plan APIs, owns all Claude calls and persistence
- **Frontend:** React (Vite) + Tailwind CSS v4 — chat UI with inline meal-plan and recipe cards
- **Database:** PostgreSQL 17 (local, via Homebrew `postgresql@17`). Database name: `franky_fitness`. Connection string in `.env` as `DATABASE_URL`. Driver: `psycopg2-binary`.
- **Data modeling:** Pydantic (`BaseModel` for structured outputs like meals, grocery lists)
- **Environment:** `python-dotenv` for loading `.env`; `venv` for package isolation
- **Recipe data:** Spoonacular Food API — provides recipes, nutritional metadata, and structured ingredient lists
- **Exercise data:** ExerciseDB via RapidAPI — ~1,300 exercises with target muscle, equipment, form instructions, and GIFs
- **API keys:** Stored in `.env` as `ANTHROPIC_API_KEY`, `SPOONACULAR_API_KEY`, and `RAPIDAPI_KEY` — never hardcode them

## Project Structure

```
franky-fitness/
├── .env                  # API keys + DATABASE_URL (gitignored)
├── .gitignore
├── CLAUDE.md             # This file
├── README.md
├── requirements.txt      # Direct dependencies
├── models.py             # Pydantic models: Person, Meal, Ingredient, WeeklyPlan, etc.
├── spoonacular.py        # Spoonacular API client — search_recipes(), get_recipe()
├── exercisedb.py         # ExerciseDB client — search_exercises(), get_exercise()
├── system_prompt.txt     # System prompt for the legacy CLI (franky.py)
├── franky.py             # Original CLI chatbot loop (superseded by the web app)
├── hello_claude.py       # First API proof-of-concept (throwaway)
├── phase-0-notes.md      # Learning journal
├── docs/
│   └── franky-fitness-prd.md   # Full product requirements doc
├── backend/              # FastAPI application
│   ├── main.py           # API routes: /api/chat, /api/plans, /api/people
│   ├── meal_agent.py     # Meal planning agent — tools, prompt builder, tool-use loop
│   ├── database.py       # psycopg2 connection + table setup (plans, agent_runs)
│   └── profiles.py       # Hardcoded Chris & Kaitlyn profiles (no auth yet)
├── frontend/             # Vite + React + Tailwind app
│   └── src/
│       ├── App.jsx       # Header + person selector (Chris / Kaitlyn)
│       ├── api.js        # fetch wrappers for the backend
│       └── components/   # Chat.jsx, MealPlanCard.jsx, RecipeCard.jsx
└── venv/                 # Virtual environment (gitignored)
```

## Architecture (Web App)

The project has moved from the Phase 0 CLI (`franky.py`) into a web app, built as **vertical slices** — each slice ships one feature through every layer (agent → API → UI → persistence) rather than building layers horizontally.

**Slice 1 (done): Meal planning end-to-end.** A user picks who they are (Chris/Kaitlyn — no auth yet, profiles are hardcoded in `backend/profiles.py`), chats with Franky, and gets a structured weekly meal plan rendered as an inline table. Plans save to PostgreSQL.

**Slice 2 (done): Recipe retrieval.** The most recently saved plan for the active person is injected into the agent's system prompt on every `/api/chat` call. The agent has a `get_recipe` tool; when the user asks how to make a meal, it resolves the meal to its Spoonacular ID from the plan, fetches full ingredients + steps, and the frontend renders a `RecipeCard`.

### How the meal agent works
- `meal_agent.run_meal_agent(messages, profile, current_plan)` runs the tool-use loop.
- Tools: `search_meals` (Spoonacular search), `get_recipe` (full recipe by ID or name), `finalize_meal_plan` (emits structured plan data).
- `_run_tool` returns a `(text_for_agent, structured_data_for_frontend)` tuple. The structured data (a finalized plan or a recipe) is surfaced back through the API response alongside the agent's text.
- The system prompt is built dynamically per request in `_build_system_prompt` — it injects the person's profile and their current saved plan. **Note:** the web app does NOT use `system_prompt.txt`; that file is only for the legacy CLI.
- Every `/api/chat` call logs token usage and latency to the `agent_runs` table.

### Running the app locally
```bash
# PostgreSQL (one-time): brew services start postgresql@17
# Terminal 1 — backend
source venv/bin/activate && uvicorn backend.main:app --reload   # :8000
# Terminal 2 — frontend
cd frontend && npm run dev                                       # :5173 (proxies /api to :8000)
```

## Decisions Made This Session
- **PostgreSQL from the start** (not SQLite) — matches the PRD target. Installed via `brew install postgresql@17`.
- **No auth yet** — Chris & Kaitlyn are hardcoded in `profiles.py`. Auth is a later slice.
- **Vertical slices over horizontal layers** — ship one feature through all layers at a time.

## Roadmap (next slices)
- Grocery list generation from a saved meal plan
- Exercise planning agent (port the logic already in `franky.py` / `exercisedb.py`)
- Multi-agent coordinator routing between meal / grocery / exercise agents
- Feedback (thumbs up/down) + preference summaries
- Email/password auth to replace hardcoded profiles

## Coding Conventions

### General
- Keep files small and single-purpose. One agent or feature per file.
- When creating a function, always add a one-line description of what it does.
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
