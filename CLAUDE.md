# Franky Fitness — CLAUDE.md

> **Start here:** Read [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) at the start of each session — it holds the architecture decisions, build order, and the running decision log. The full product vision is in [`docs/franky-fitness-prd.md`](docs/franky-fitness-prd.md).

## What This Project Is

Franky Fitness is a meal planning, exercise, and grocery assistant built for a couple. It uses the Anthropic Python SDK to power a conversational AI agent (Franky) that helps plan meals, suggest workouts, and generate grocery lists tailored to two people's preferences and goals.

The architecture is two LLM specialists — meal planning (which also covers nutrition guidance) and exercise planning — coordinated through a single conversation interface by a Haiku-based router (`backend/coordinator.py`). Grocery list generation is deterministic code, not an agent (see `docs/IMPLEMENTATION_PLAN.md`, Decision 3).

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
├── models.py             # Pydantic models: Person, Meal, Ingredient, GroceryItem, WeeklyPlan, etc.
├── spoonacular.py        # Spoonacular API client — search_recipes(), get_recipe()
├── exercisedb.py         # ExerciseDB client — search_exercises(), get_exercise()
├── grocery.py            # Pure code: generate_grocery_list() sums + categorizes ingredients from a saved plan
├── system_prompt.txt     # System prompt for the legacy CLI (franky.py)
├── franky.py             # Original CLI chatbot loop (superseded by the web app)
├── hello_claude.py       # First API proof-of-concept (throwaway)
├── phase-0-notes.md      # Learning journal
├── docs/
│   └── franky-fitness-prd.md   # Full product requirements doc
├── backend/              # FastAPI application
│   ├── main.py           # API routes: /api/chat, /api/plans, /api/plans/{id}/grocery-list, /api/people
│   ├── coordinator.py    # Routes each turn to the meal or exercise specialist (Haiku classifier)
│   ├── meal_agent.py     # Meal planning agent — tools, prompt builder, tool-use loop
│   ├── exercise_agent.py # Exercise planning agent — tools, prompt builder, tool-use loop
│   ├── database.py       # psycopg2 connection + table setup (plans, agent_runs)
│   └── profiles.py       # Hardcoded Chris & Kaitlyn profiles (no auth yet)
├── frontend/             # Vite + React + Tailwind app
│   └── src/
│       ├── App.jsx       # Header + person selector (Chris / Kaitlyn)
│       ├── api.js        # fetch wrappers for the backend
│       └── components/   # Chat.jsx, MealPlanCard.jsx, RecipeCard.jsx, GroceryListCard.jsx, WorkoutPlanCard.jsx
└── venv/                 # Virtual environment (gitignored)
```

## Architecture (Web App)

The project has moved from the Phase 0 CLI (`franky.py`) into a web app, built as **vertical slices** — each slice ships one feature through every layer (agent → API → UI → persistence) rather than building layers horizontally.

**Slice 1 (done): Meal planning end-to-end.** A user picks who they are (Chris/Kaitlyn — no auth yet, profiles are hardcoded in `backend/profiles.py`), chats with Franky, and gets a structured weekly meal plan rendered as an inline table. Plans save to PostgreSQL.

**Slice 2 (done): Recipe retrieval.** The most recently saved plan for the active person is injected into the agent's system prompt on every `/api/chat` call. The agent has a `get_recipe` tool; when the user asks how to make a meal, it resolves the meal to its Spoonacular ID from the plan, fetches full ingredients + steps, and the frontend renders a `RecipeCard`.

**Slice 3 (done): Grocery list generation.** When `finalize_meal_plan` is called, each meal's full ingredient list is fetched from Spoonacular and stored alongside the plan. `grocery.py` is pure code — no agent, no LLM call — that sums ingredient quantities across a saved plan and categorizes each item by store section via a static keyword lookup. Triggered two ways: (1) a "Grocery List" button on a saved `MealPlanCard` calls `GET /api/plans/{id}/grocery-list`, or (2) typing "grocery list" / "shopping list" in chat — `/api/chat` detects this intent and short-circuits to `generate_grocery_list()` before reaching the agent. Either way, the frontend renders a `GroceryListCard` grouped by category.

**Slice 4 (done): Exercise agent + coordinator routing.** `backend/exercise_agent.py` is the second LLM specialist, mirroring the meal agent's structure over ExerciseDB. `backend/coordinator.py` classifies each turn — every `/api/chat` call first sends the latest user message to Haiku with a forced `route` tool call (`agent` ∈ `{"meal", "exercise"}`, default "meal" if ambiguous), then dispatches the full conversation to the chosen specialist. The frontend renders a `WorkoutPlanCard` for finalized workout plans, with a "Save Plan" button that persists as `type='workout_plan'`.

### How the meal agent works
- `meal_agent.run_meal_agent(messages, profile, current_plan)` runs the tool-use loop.
- Tools: `search_meals` (Spoonacular search), `get_recipe` (full recipe by ID or name), `finalize_meal_plan` (emits structured plan data).
- `_run_tool` returns a `(text_for_agent, structured_data_for_frontend)` tuple. The structured data (a finalized plan or a recipe) is surfaced back through the API response alongside the agent's text.
- The system prompt is built dynamically per request in `_build_system_prompt` — it injects the person's profile and their current saved plan. **Note:** the web app does NOT use `system_prompt.txt`; that file is only for the legacy CLI.

### How the exercise agent works
- `exercise_agent.run_exercise_agent(messages, profile, current_plan)` mirrors the meal agent's tool-use loop.
- Tools: `search_exercises` (ExerciseDB search by name/body part/target muscle/equipment), `finalize_workout_plan` (emits structured workout_days/rest_days/notes).
- The system prompt asks the user about training days, equipment, and injuries before building a plan, and instructs the agent to use real exercise IDs/names from `search_exercises`.

### How the coordinator works
- `coordinator.run_coordinator(messages, profile, current_meal_plan, current_workout_plan)` classifies the latest user message via `claude-haiku-4-5-20251001` with `tool_choice` forced to a `route` tool (enum `["meal", "exercise"]`), then calls `run_meal_agent` or `run_exercise_agent` with the full conversation.
- **Important:** the routing call needs `max_tokens >= ~50` — at `max_tokens=20` Haiku returns an empty tool input and the code silently falls back to "meal" with no error. Currently set to 200.
- Returns `agent_runs`: one entry for the coordinator call and one for the chosen specialist; `/api/chat` logs both to the `agent_runs` table with `agent_type` ∈ `{"coordinator", "meal_agent", "exercise_agent"}`.

### Running the app locally
```bash
# PostgreSQL (one-time): brew services start postgresql@17
# Terminal 1 — backend
source venv/bin/activate && uvicorn backend.main:app --reload   # :8000
# Terminal 2 — frontend
cd frontend && npm run dev                                       # :5173 (proxies /api to :8000)
```

### Debugging: checking which agent handled a turn
Query `agent_runs` directly to see what the coordinator decided:
```bash
psql franky_fitness -c "SELECT id, agent_type, person_name, created_at FROM agent_runs ORDER BY id DESC LIMIT 6;"
```
A successful turn inserts **two rows** with the same `created_at`: `coordinator` (the routing call) followed by `meal_agent` or `exercise_agent` (the specialist that handled it).

**Caveat:** `agent_runs` only gets written on a fully successful turn. Two cases write nothing:
- The grocery-list short-circuit ("grocery list" / "shopping list" in the message) — pure code, never reaches the coordinator.
- A failed coordinator/specialist call (`RuntimeError` → HTTP 502) — the exception is raised before the insert.

So "no new rows after sending a message" means either it hit the grocery shortcut or the request errored — check `/tmp/uvicorn.log` or the browser's network tab for a non-200 response.

## Decisions Made This Session
- **PostgreSQL from the start** (not SQLite) — matches the PRD target. Installed via `brew install postgresql@17`.
- **No auth yet** — Chris & Kaitlyn are hardcoded in `profiles.py`. Auth is a later slice.
- **Vertical slices over horizontal layers** — ship one feature through all layers at a time.

## Roadmap (next slices)
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
