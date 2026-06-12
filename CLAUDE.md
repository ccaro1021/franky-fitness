# Franky Fitness — CLAUDE.md

> **Start here:** Read [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) at the start of each session — it holds the architecture decisions, build order, and the running decision log. The full product vision is in [`docs/franky-fitness-prd.md`](docs/franky-fitness-prd.md).

## What This Project Is

Franky Fitness is a meal planning, exercise, and grocery assistant built for a couple. It uses the Anthropic Python SDK to power a conversational AI agent (Franky) that helps plan meals, suggest workouts, and generate grocery lists tailored to two people's preferences and goals.

The architecture is two LLM specialists — meal planning (which also covers nutrition guidance) and exercise planning — coordinated through a single conversation interface by a Haiku-based router (`backend/coordinator.py`). Grocery list generation is deterministic code, not an agent (see `docs/IMPLEMENTATION_PLAN.md`, Decision 3).

## Who It's For

**Chris and Kaitlyn.** Both partners' needs, preferences, and dietary restrictions should always be considered. Features should be designed for two people, not one. Each has their own account (email/password login) and profile.

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
│   ├── main.py           # API routes: /api/auth/*, /api/profile, /api/chat, /api/plans, /api/plans/{id}/grocery-list, /api/feedback
│   ├── auth.py           # Password hashing (bcrypt), session create/lookup/delete, get_current_user dependency
│   ├── users.py          # User + profile CRUD, BMI computation, builds profile context for agent prompts
│   ├── migrate_to_auth.py # One-time interactive migration: seeds Chris & Kaitlyn accounts, person_name -> user_id
│   ├── coordinator.py    # Routes each turn to the meal or exercise specialist (Haiku classifier)
│   ├── meal_agent.py     # Meal planning agent — tools, prompt builder, tool-use loop
│   ├── exercise_agent.py # Exercise planning agent — tools, prompt builder, tool-use loop
│   ├── preferences.py    # Pure code: records feedback and derives a per-user preference summary
│   └── database.py       # psycopg2 connection + table setup (users, profiles, sessions, plans, agent_runs, feedback, preference_summaries)
├── frontend/             # Vite + React + Tailwind app
│   └── src/
│       ├── App.jsx       # Auth gate (login/signup vs. app shell), header with user name + Profile/Logout
│       ├── api.js        # fetch wrappers for the backend (credentials: 'include' for session cookies)
│       └── components/   # Chat.jsx, AuthPage.jsx, ProfilePage.jsx, MealPlanCard.jsx, RecipeCard.jsx, GroceryListCard.jsx, WorkoutPlanCard.jsx, FeedbackButtons.jsx
└── venv/                 # Virtual environment (gitignored)
```

## Architecture (Web App)

The project has moved from the Phase 0 CLI (`franky.py`) into a web app, built as **vertical slices** — each slice ships one feature through every layer (agent → API → UI → persistence) rather than building layers horizontally.

**Slice 1 (done): Meal planning end-to-end.** A user logs in, chats with Franky, and gets a structured weekly meal plan rendered as an inline table. Plans save to PostgreSQL.

**Slice 2 (done): Recipe retrieval.** The most recently saved plan for the active person is injected into the agent's system prompt on every `/api/chat` call. The agent has a `get_recipe` tool; when the user asks how to make a meal, it resolves the meal to its Spoonacular ID from the plan, fetches full ingredients + steps, and the frontend renders a `RecipeCard`.

**Slice 3 (done): Grocery list generation.** When `finalize_meal_plan` is called, each meal's full ingredient list is fetched from Spoonacular and stored alongside the plan. `grocery.py` is pure code — no agent, no LLM call — that sums ingredient quantities across a saved plan and categorizes each item by store section via a static keyword lookup. Triggered two ways: (1) a "Grocery List" button on a saved `MealPlanCard` calls `GET /api/plans/{id}/grocery-list`, or (2) typing "grocery list" / "shopping list" in chat — `/api/chat` detects this intent and short-circuits to `generate_grocery_list()` before reaching the agent. Either way, the frontend renders a `GroceryListCard` grouped by category.

**Slice 4 (done): Exercise agent + coordinator routing.** `backend/exercise_agent.py` is the second LLM specialist, mirroring the meal agent's structure over ExerciseDB. `backend/coordinator.py` classifies each turn — every `/api/chat` call first sends the latest user message to Haiku with a forced `route` tool call (`agent` ∈ `{"meal", "exercise"}`, default "meal" if ambiguous), then dispatches the full conversation to the chosen specialist. The frontend renders a `WorkoutPlanCard` for finalized workout plans, with a "Save Plan" button that persists as `type='workout_plan'`.

**Slice 5 (done): Feedback + preference summaries.** Once a meal plan or workout plan is saved, each meal/exercise row gets 👍/👎 `FeedbackButtons` (with an optional "+ note") that call `POST /api/feedback`. `backend/preferences.py` is pure code — no agent, no LLM call — that records the rating to the `feedback` table and recomputes a `preference_summaries` row: for each `(item_type, item_name)`, the most recent rating wins, bucketed into `liked_meals` / `disliked_meals` / `liked_workouts` / `disliked_workouts`. `/api/chat` fetches this summary and passes it to whichever specialist runs; both `_build_system_prompt` functions append a "Known preferences" block when any bucket is non-empty.

**Slice 6 (done): Auth + user profiles.** Replaced hardcoded `backend/profiles.py` with real accounts. `backend/auth.py` handles bcrypt password hashing and a DB-backed `sessions` table; `get_current_user` is a FastAPI dependency that reads the `session_token` httponly cookie. New `users` and `profiles` tables (`backend/users.py`) hold email/password/name and height_inches/weight_lbs/target_weight_lbs/dietary_restrictions/fitness_goals/notes — BMI is computed on the fly via `compute_bmi`, never stored. The frontend gates on `GET /api/auth/me`: unauthenticated users see `AuthPage` (login/signup toggle); authenticated users see the chat plus a `ProfilePage` for editing their stats. `plans`/`agent_runs`/`feedback`/`preference_summaries` now key on `user_id` instead of `person_name` (migrated via the one-time `backend/migrate_to_auth.py`). Both agents' system prompts include a "stats" block (height/weight/target/BMI) when those fields are set.

**Slice 7 (done): View/correct preference summary (PRD stories 63-64).** `GET /api/preferences` returns the user's `preference_summaries` row (or an empty `EMPTY_SUMMARY` shape if no feedback yet). `ProfilePage` renders a "What Franky Knows About You" section listing `liked_meals`/`disliked_meals`/`liked_workouts`/`disliked_workouts` as removable tags. Clicking the `×` on a tag calls `POST /api/preferences/forget` (`backend/preferences.forget_item`), which deletes that user's `feedback` rows for the `(item_type, item_name)` and recomputes the summary — so a corrected preference won't reappear unless the user re-rates that item.

### How the meal agent works
- `meal_agent.run_meal_agent(messages, profile, current_plan)` runs the tool-use loop.
- Tools: `search_meals` (Spoonacular search), `get_recipe` (full recipe by ID or name), `finalize_meal_plan` (emits structured plan data).
- `_run_tool` returns a `(text_for_agent, structured_data_for_frontend)` tuple. The structured data (a finalized plan or a recipe) is surfaced back through the API response alongside the agent's text.
- The system prompt is built dynamically per request in `_build_system_prompt` — it injects the user's profile (dietary restrictions, fitness goals, notes, and — when set — height/weight/target weight/BMI via `_format_stats_for_prompt`) and their current saved plan. **Note:** the web app does NOT use `system_prompt.txt`; that file is only for the legacy CLI.

### How the exercise agent works
- `exercise_agent.run_exercise_agent(messages, profile, current_plan)` mirrors the meal agent's tool-use loop.
- Tools: `search_exercises` (ExerciseDB search by name/body part/target muscle/equipment), `finalize_workout_plan` (emits structured workout_days/rest_days/notes).
- The system prompt asks the user about training days, equipment, and injuries before building a plan, and instructs the agent to use real exercise IDs/names from `search_exercises`.

### How the coordinator works
- `coordinator.run_coordinator(messages, profile, current_meal_plan, current_workout_plan)` classifies the latest user message via `claude-haiku-4-5-20251001` with `tool_choice` forced to a `route` tool (enum `["meal", "exercise"]`), then calls `run_meal_agent` or `run_exercise_agent` with the full conversation.
- **Important:** the routing call needs `max_tokens >= ~50` — at `max_tokens=20` Haiku returns an empty tool input and the code silently falls back to "meal" with no error. Currently set to 200.
- Returns `agent_runs`: one entry for the coordinator call and one for the chosen specialist; `/api/chat` logs both to the `agent_runs` table with `agent_type` ∈ `{"coordinator", "meal_agent", "exercise_agent"}`.

### How feedback and preferences work
- `preferences.record_feedback(user_id, plan_id, item_type, item_name, rating, note)` inserts a row into `feedback`, then calls `_recompute_summary` and upserts `preference_summaries`.
- `_recompute_summary` selects the most recent rating per `(item_type, item_name)` (`SELECT DISTINCT ON ... ORDER BY ... created_at DESC`) and buckets into `liked_meals` / `disliked_meals` / `liked_workouts` / `disliked_workouts`. The `patterns` field exists in the schema but is left empty — deriving it would need model judgment, which is out of scope until there's a reason to add an LLM call here.
- `/api/chat` calls `get_preference_summary(user_id)` and passes it to `run_coordinator`, which forwards it unchanged to whichever specialist runs.
- **Diverges from the PRD's `plan_items` table:** plans stay a single JSONB blob. Feedback is keyed by `(user_id, item_type, item_name)` plus an optional `plan_id` for traceability — `item_name` (the dish/exercise name) is what's actually useful for "don't suggest this again."
- `forget_item(user_id, item_type, item_name)` deletes all `feedback` rows for that `(user_id, item_type, item_name)` and recomputes the summary — this is how a user "corrects" Franky's understanding (PRD story 64): the item drops out of its bucket and won't return unless re-rated.

### How auth and profiles work
- `backend/auth.py`: `hash_password`/`verify_password` (bcrypt); `create_session(user_id)` generates a token and stores it in `sessions` with a 30-day expiry; `get_current_user` is a FastAPI dependency that reads the `session_token` cookie, looks up the session, and raises 401 if missing/expired.
- `backend/users.py`: `create_user`, `get_user_by_email`, `get_profile`/`update_profile` (height_inches, weight_lbs, target_weight_lbs, dietary_restrictions, fitness_goals, notes), `compute_bmi(height_inches, weight_lbs)` (returns `None` if either is missing — BMI is never stored), `build_profile_context(user_id)` shapes all of this into the dict the agents' `_build_system_prompt` expects.
- Routes: `POST /api/auth/signup|login|logout`, `GET /api/auth/me`, `GET`/`PUT /api/profile`. The session cookie is httponly, `SameSite=Lax`, no `Secure` flag (local http dev).
- Frontend: `App.jsx` calls `GET /api/auth/me` on mount; unauthenticated → `AuthPage` (login/signup toggle); authenticated → header (name, Profile/Chat toggle, Logout) + `Chat` or `ProfilePage`. All `api.js` fetches use `credentials: 'include'`.

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
psql franky_fitness -c "SELECT id, agent_type, user_id, created_at FROM agent_runs ORDER BY id DESC LIMIT 6;"
```
A successful turn inserts **two rows** with the same `created_at`: `coordinator` (the routing call) followed by `meal_agent` or `exercise_agent` (the specialist that handled it).

**Caveat:** `agent_runs` only gets written on a fully successful turn. Two cases write nothing:
- The grocery-list short-circuit ("grocery list" / "shopping list" in the message) — pure code, never reaches the coordinator.
- A failed coordinator/specialist call (`RuntimeError` → HTTP 502) — the exception is raised before the insert.

So "no new rows after sending a message" means either it hit the grocery shortcut or the request errored — check `/tmp/uvicorn.log` or the browser's network tab for a non-200 response.

## Decisions Made This Session
- **PostgreSQL from the start** (not SQLite) — matches the PRD target. Installed via `brew install postgresql@17`.
- **Session-cookie auth** (not JWT) — `users`/`profiles`/`sessions` tables, bcrypt password hashing, replacing hardcoded `profiles.py`.
- **Vertical slices over horizontal layers** — ship one feature through all layers at a time.

## Roadmap (next slices)
- **Slice 8 (planned, not started): transcript observability + eval harness.** Full execution spec in [`docs/SLICE_8_OBSERVABILITY_EVALS_PLAN.md`](docs/SLICE_8_OBSERVABILITY_EVALS_PLAN.md). Phase 1: capture a canonical JSONL `Transcript` per agent call (system/messages/tool-calls/output/outcome/tokens/latency/`agent_invoked`), demote `agent_runs` to a queryable index (no prompt content in the DB), add a `backend/view_transcript.py` CLI. Phase 2: an `evals/` harness (Task/Trial/Grader, code-based + LLM-as-judge, pass@k/pass^k) that replays tasks through `run_coordinator` using the same Transcript format. Mapped to Anthropic's "Demystifying Evals for AI Agents." See the 2026-06-12 decision-log entry in IMPLEMENTATION_PLAN.md for the design rationale.

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
