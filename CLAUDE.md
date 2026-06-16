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
├── models.py             # Pydantic models: Meal, Ingredient, GroceryItem, Exercise
├── spoonacular.py        # Spoonacular API client — search_recipes(), get_recipe()
├── exercisedb.py         # ExerciseDB client — search_exercises(), get_exercise()
├── grocery.py            # Pure code: generate_grocery_list() sums + categorizes ingredients by canonical_name
├── docs/
│   └── franky-fitness-prd.md   # Full product requirements doc
├── backend/              # FastAPI application
│   ├── main.py           # API routes: /api/auth/*, /api/profile, /api/chat, /api/plans, /api/plans/{id}, /api/plans/{id}/grocery-list, /api/feedback, /api/saved-recipes
│   ├── auth.py           # Password hashing (bcrypt), session create/lookup/delete, get_current_user dependency
│   ├── users.py          # User + profile CRUD, BMI computation, builds profile context for agent prompts
│   ├── migrate_to_auth.py # One-time interactive migration: seeds Chris & Kaitlyn accounts, person_name -> user_id
│   ├── coordinator.py    # Routes each turn to the meal or exercise specialist (Haiku classifier)
│   ├── meal_agent.py     # Meal planning agent — tools, prompt builder, tool-use loop
│   ├── exercise_agent.py # Exercise planning agent — tools, prompt builder, tool-use loop
│   ├── preferences.py    # Pure code: records feedback and derives a per-user preference summary
│   ├── grocery_agent.py  # Ingredient name normalization — single batch LLM call, backed by ingredient_normalizations cache
│   ├── saved_recipes.py  # Pure code: save_recipe/list_saved_recipes/delete_saved_recipe over saved_recipes table
│   ├── transcripts.py    # Transcript schema + serialize_messages/extract_steps/write_transcript/read_transcripts/promote_to_task
│   ├── view_transcript.py # CLI to inspect transcripts/*.jsonl (--last/--agent/--invoked/--id)
│   └── database.py       # psycopg2 connection + table setup (users, profiles, sessions, plans, agent_runs, feedback, preference_summaries, ingredient_normalizations, saved_recipes)
├── evals/                # Eval harness (Task/Trial/Grader, pass@k/pass^k)
│   ├── tasks.py          # Seed Task set (inputs, synthetic profile, graders)
│   ├── graders.py        # Code-based + LLM-as-judge graders, each (transcript) -> {assertion, passed, reasoning}
│   ├── harness.py         # python -m evals.harness --trials N [--task ID]
│   ├── grocery_normalization.py # python -m evals.grocery_normalization — normalization pattern generalization
│   └── README.md          # How to run + how to add a task from a real failure
├── transcripts/          # Gitignored JSONL Transcript records, one file per day
├── tests/                # stdlib unittest suite — test_grocery.py covers summing/categorization (no API calls); test_saved_items.py is DB-backed (TestClient against the local Postgres db)
├── frontend/             # Vite + React + Tailwind app
│   └── src/
│       ├── App.jsx       # Auth gate (login/signup vs. app shell), header with user name + Chat/Saved/Profile nav + Logout
│       ├── api.js        # fetch wrappers for the backend (credentials: 'include' for session cookies)
│       └── components/   # Chat.jsx, AuthPage.jsx, ProfilePage.jsx, SavedItemsPage.jsx, MealPlanCard.jsx, RecipeCard.jsx, GroceryListCard.jsx, WorkoutPlanCard.jsx, FeedbackButtons.jsx
└── venv/                 # Virtual environment (gitignored)
```

## Architecture (Web App)

The project has moved from the Phase 0 CLI (`franky.py`) into a web app, built as **vertical slices** — each slice ships one feature through every layer (agent → API → UI → persistence) rather than building layers horizontally.

**Slice 1 (done): Meal planning end-to-end.** A user logs in, chats with Franky, and gets a structured weekly meal plan rendered as an inline table. Plans save to PostgreSQL.

**Slice 2 (done): Recipe retrieval.** The most recently saved plan for the active person is injected into the agent's system prompt on every `/api/chat` call. The agent has a `get_recipe` tool; when the user asks how to make a meal, it resolves the meal to its Spoonacular ID from the plan, fetches full ingredients + steps, and the frontend renders a `RecipeCard`.

**Slice 3 (done, revised by Slices 9-10): Grocery list generation.** `grocery.py` is pure code — no agent, no LLM call — that sums ingredient quantities across a saved plan, grouped by `(canonical_name, unit)`, and reads each item's `category` directly from plan data (see Slice 10). Triggered two ways: (1) a "Grocery List" button on a saved `MealPlanCard` calls `GET /api/plans/{id}/grocery-list`, or (2) typing "grocery list" / "shopping list" in chat — `/api/chat` detects this intent and short-circuits before reaching the agent. Either way, the frontend renders a `GroceryListCard` grouped by category. Ingredient fetching, name normalization, and unit/category reconciliation now happen at grocery-list-request time (Slices 9-10), not at `finalize_meal_plan` time.

**Slice 4 (done): Exercise agent + coordinator routing.** `backend/exercise_agent.py` is the second LLM specialist, mirroring the meal agent's structure over ExerciseDB. `backend/coordinator.py` classifies each turn — every `/api/chat` call first sends the latest user message to Haiku with a forced `route` tool call (`agent` ∈ `{"meal", "exercise"}`, default "meal" if ambiguous), then dispatches the full conversation to the chosen specialist. The frontend renders a `WorkoutPlanCard` for finalized workout plans, with a "Save Plan" button that persists as `type='workout_plan'`.

**Slice 5 (done): Feedback + preference summaries.** Once a meal plan or workout plan is saved, each meal/exercise row gets 👍/👎 `FeedbackButtons` (with an optional "+ note") that call `POST /api/feedback`. `backend/preferences.py` is pure code — no agent, no LLM call — that records the rating to the `feedback` table and recomputes a `preference_summaries` row: for each `(item_type, item_name)`, the most recent rating wins, bucketed into `liked_meals` / `disliked_meals` / `liked_workouts` / `disliked_workouts`. `/api/chat` fetches this summary and passes it to whichever specialist runs; both `_build_system_prompt` functions append a "Known preferences" block when any bucket is non-empty.

**Slice 6 (done): Auth + user profiles.** Replaced hardcoded `backend/profiles.py` with real accounts. `backend/auth.py` handles bcrypt password hashing and a DB-backed `sessions` table; `get_current_user` is a FastAPI dependency that reads the `session_token` httponly cookie. New `users` and `profiles` tables (`backend/users.py`) hold email/password/name and height_inches/weight_lbs/target_weight_lbs/dietary_restrictions/fitness_goals/notes — BMI is computed on the fly via `compute_bmi`, never stored. The frontend gates on `GET /api/auth/me`: unauthenticated users see `AuthPage` (login/signup toggle); authenticated users see the chat plus a `ProfilePage` for editing their stats. `plans`/`agent_runs`/`feedback`/`preference_summaries` now key on `user_id` instead of `person_name` (migrated via the one-time `backend/migrate_to_auth.py`). Both agents' system prompts include a "stats" block (height/weight/target/BMI) when those fields are set.

**Slice 7 (done): View/correct preference summary (PRD stories 63-64).** `GET /api/preferences` returns the user's `preference_summaries` row (or an empty `EMPTY_SUMMARY` shape if no feedback yet). `ProfilePage` renders a "What Franky Knows About You" section listing `liked_meals`/`disliked_meals`/`liked_workouts`/`disliked_workouts` as removable tags. Clicking the `×` on a tag calls `POST /api/preferences/forget` (`backend/preferences.forget_item`), which deletes that user's `feedback` rows for the `(item_type, item_name)` and recomputes the summary — so a corrected preference won't reappear unless the user re-rates that item.

**Slice 8 (done): Transcript observability + eval harness.** Full spec in [`docs/SLICE_8_OBSERVABILITY_EVALS_PLAN.md`](docs/SLICE_8_OBSERVABILITY_EVALS_PLAN.md). Every agent call (coordinator routing + meal/exercise specialist) builds a `Transcript` (`backend/transcripts.py`) — system prompt, full serialized message history, extracted tool-call steps, final output, structured outcome, token usage, latency, model, `agent_type`, `agent_invoked`. `/api/chat` appends each turn's transcripts to gitignored `transcripts/<date>.jsonl` and logs `agent_invoked`/`transcript_id` pointer columns on `agent_runs` — no prompt content reaches Postgres. `python -m backend.view_transcript [--last N] [--agent ...] [--invoked ...] [--id ...]` pretty-prints them. The `evals/` package replays a seed set of 7 tasks through `run_coordinator()` (DB-free) for `k` trials via `python -m evals.harness --trials N [--task ID]`, grades each trial's Transcript with code-based + LLM-as-judge graders, and reports pass@k/pass^k.

**Slice 9 (done): Grocery normalization agent.** Full spec in [`docs/SLICE_9_GROCERY_AGENT_PLAN.md`](docs/SLICE_9_GROCERY_AGENT_PLAN.md). Replaces the hand-maintained `_INGREDIENT_ALIASES` dict with an LLM-backed normalization step — a hybrid, not a full grocery agent (summing in `grocery.py` is unchanged; categorization was later moved to the LLM too, see Slice 10). `finalize_meal_plan` no longer fetches ingredients; instead each meal gets `ingredients_fetched: false`. At grocery-list-request time (either route), `backend/main.py:_prepare_grocery_data` fetches ingredients for any meal missing them via `spoonacular.get_recipe` (failures leave that meal pending for next time), collects raw ingredient names without a `canonical_name`, and calls `backend.grocery_agent.normalize_ingredients` — which checks the global `ingredient_normalizations` cache table (seeded from the old alias dict + self-maps) and only calls `claude-opus-4-1-20250805` in one batch for cache misses, upserting results back into the cache. The per-ingredient `canonical_name` and per-meal `ingredients_fetched` flag are persisted onto `plans.content` so repeat requests are pure code. `python -m evals.grocery_normalization` checks that novel ingredient strings still follow the audited patterns (fresh/dried, color variants, prepared-form != raw-form).

**Slice 10 (done): Grocery quantity reconciliation + categorization.** Adds a second LLM step to `_prepare_grocery_data`, run after name normalization: for every ingredient that has a `canonical_name` but no `category` yet, collects the distinct `(canonical_name, unit)` pairs across the plan and calls `backend.grocery_agent.reconcile_quantities` — one batch call to `claude-opus-4-1-20250805` (forced `reconcile_units` tool) that, per canonical ingredient, picks a single shopping `target_unit`, gives a `multiplier` to convert each seen unit into it, and assigns a `category` (`produce`/`fruit`/`protein`/`dairy_eggs`/`carbs`/`pantry`, the same set `GroceryListCard` groups by). For each ingredient, `quantity_per_serving` is multiplied by its unit's `multiplier`, `unit` becomes `target_unit`, and `category` is set — all persisted onto `plans.content` like Slice 9's fields, so it only runs once per plan. `grocery.generate_grocery_list` is now pure summing/grouping by `(canonical_name, unit)` with `category` read straight off the ingredient (defaulting to `"pantry"` for plans saved before this slice) — no keyword-based categorization. `_prepare_grocery_data` now returns `(plan, transcripts)` where `transcripts` has 0-2 entries (normalizer, reconciler); `python -m evals.grocery_normalization` includes a `cross_unit_olive_oil`-style task checking the reconciler's unit-conversion and categorization judgment.

**Slice 12 (done): Grocery category set update.** Reworked the store-section categories from `produce`/`protein`/`dairy`/`frozen`/`pantry` to `produce`/`fruit`/`protein`/`dairy_eggs`/`carbs`/`pantry` — `backend/grocery_agent.py`'s `SYSTEM_PROMPT_RECONCILE` and `TOOLS_RECONCILE` enum and `frontend/src/components/GroceryListCard.jsx`'s `CATEGORY_ORDER`/`CATEGORY_LABELS`/`CATEGORY_ICONS` were updated to match; frozen items are now categorized by what they are (e.g. frozen vegetables -> `produce`) rather than having their own bucket. `backend/migrate_grocery_categories.py` is a one-time script (`python -m backend.migrate_grocery_categories`) that strips the cached `category` field from every saved meal plan's ingredients, so the next grocery-list request for each plan re-runs `reconcile_quantities` under the new category set.

**Slice 13 (done): Profile onboarding + chat-driven profile updates.** Full spec in [`docs/SLICE_13_PROFILE_ONBOARDING_PLAN.md`](docs/SLICE_13_PROFILE_ONBOARDING_PLAN.md). **Onboarding (frontend-only):** `AuthPage`'s signup path calls `onAuth(user, { isNewSignup: true })`; login passes `isNewSignup: false`. `App.jsx` sets its initial `view` to `'profile'` on a new signup and passes `showOnboardingBanner` to `ProfilePage`, which renders a dismissible banner above the Stats card explaining why profile info helps Franky — dismissing it only clears local state, no DB column. `Chat.jsx`'s initial greeting gets an extra sentence inviting the user to share stats/goals/restrictions in chat or via Profile when `isNewSignup` is true. **`update_profile` tool:** added to both `meal_agent.TOOLS` and `exercise_agent.TOOLS` with an identical schema — `height_inches`/`weight_lbs`/`target_weight_lbs` (overwrite), `add_dietary_restrictions`/`add_fitness_goals` (merged into existing lists, case-insensitive de-duped), `append_notes` (appended on a new line). New `backend.users.patch_profile(user_id, **fields)` does the partial update/merge/append and returns the refreshed profile (same shape as `get_profile`, including `bmi`). `_run_tool` in both agents takes a `user_id: int | None` (threaded through `run_meal_agent`/`run_exercise_agent`/`run_coordinator` from `/api/chat`, which passes `user["id"]`); when `user_id` is set it calls `patch_profile`, and either way it returns a plain-language `tool_result` (e.g. "Noted: weight to 165 lbs; added 'vegetarian' to dietary restrictions.") built from `_describe_profile_update(inputs)` — so the eval harness (`user_id=None`) gets a descriptive tool_result without a DB write. Both agents' system prompts instruct Franky to call `update_profile` for durable info (not one-off preferences) and confirm what was saved in plain language. **Pre-finalize reminder:** `_profile_incomplete(profile)` (empty `fitness_goals` OR both `height_inches`/`weight_lbs` unset for the meal agent; empty `fitness_goals` for the exercise agent) adds one sentence to the system prompt instructing Franky to mention, alongside `finalize_meal_plan`/`finalize_workout_plan`, that providing that info would help tailor the plan — computed once per system-prompt build from the existing `profile` dict, no new context plumbing. **Tests:** `tests/test_users.py` (new, DB-backed, mirrors `tests/test_saved_items.py`) covers `patch_profile`'s scalar overwrite/partial-update, list merge/dedupe, notes append (including no leading blank line on first append), and returned-shape parity with `get_profile`. `evals/tasks.py` gains `profile_update_from_chat` (graded by new `called_tool_with(tool_name, expected_fields)` in `evals/graders.py`, checking `update_profile` was called with the right height/weight/dietary-restriction fields) and `profile_reminder_when_empty` (an empty-profile synthetic user requests a plan; `judge()` checks the reply mentions profile completeness).

**Slice 11 (done): Saved Items.** New `saved_recipes` table (`id`, `user_id`, `content` JSONB, `created_at`) mirrors the `plans` table pattern; `backend/saved_recipes.py` is a thin CRUD wrapper (`save_recipe`, `list_saved_recipes`, `delete_saved_recipe`), all scoped by `user_id`. New routes in `backend/main.py`: `POST`/`GET /api/saved-recipes`, `DELETE /api/saved-recipes/{id}`, and `DELETE /api/plans/{id}` (all 404 if not found or not owned by the current user). The frontend gets a third "Saved" pill in the header nav (`App.jsx`) alongside Chat/Profile, routing to `SavedItemsPage` — internal Meal Plans / Workout Plans / Recipes sub-tabs, each lazily fetching its list (`listPlans('meal_plan' | 'workout_plan')` / `listSavedRecipes()`) on first activation. Each row shows a date-stamped summary (meal count × days, workout day count, or recipe name + macros) with a confirm-gated `×` to delete (`deletePlan`/`deleteSavedRecipe`); clicking a row expands it into the same `MealPlanCard`/`WorkoutPlanCard`/`RecipeCard` used elsewhere, seeded via new `savedPlanId`/`initiallySaved` props so they render directly in post-save state (feedback buttons, Grocery List button). `RecipeCard` also gets a header-bar Save/Saved button (calls `saveRecipe`) so individually-surfaced recipes ("how do I make X") can be saved on their own — saving the same recipe twice is allowed and creates two rows, consistent with plan-saving. `tests/test_saved_items.py` is the first DB-backed test module — `unittest` + FastAPI `TestClient` against the local Postgres db, covering save/list/delete, double-save, plan deletion, and cross-user ownership checks (404, never another user's data).

### How the meal agent works
- `meal_agent.run_meal_agent(messages, profile, current_plan)` runs the tool-use loop, capped at `MAX_TURNS = 10` round-trips. If hit, the loop bails out with a fallback "too much back-and-forth" message and `outcome["hit_max_turns"] = True` in the transcript, instead of looping indefinitely.
- Tools: `search_meals` (Spoonacular search), `get_recipe` (full recipe by ID or name), `finalize_meal_plan` (emits structured plan data). Tool descriptions explicitly delineate boundaries: `search_meals` is for plan-building (call once per meal slot, use its values as-is), `get_recipe` is ONLY for explicit "how do I make X" requests (never during plan-building). `finalize_meal_plan` does NOT fetch ingredients — it marks each meal `ingredients_fetched: false`; ingredients are fetched and normalized lazily at grocery-list-request time (Slice 9).
- `_run_tool` returns a `(text_for_agent, structured_data_for_frontend)` tuple. The structured data (a finalized plan or a recipe) is surfaced back through the API response alongside the agent's text.
- The system prompt is built dynamically per request in `_build_system_prompt` — it injects the user's profile (dietary restrictions, fitness goals, notes, and — when set — height/weight/target weight/BMI via `_format_stats_for_prompt`) and their current saved plan. It also instructs the agent to state, in one sentence, what it's about to search for and why before each `search_meals` call — these intermediate text blocks are captured automatically in the transcript's `messages`/`steps` for observability.

### How the exercise agent works
- `exercise_agent.run_exercise_agent(messages, profile, current_plan)` mirrors the meal agent's tool-use loop, including the `MAX_TURNS = 10` guardrail and `outcome["hit_max_turns"]`.
- Tools: `search_exercises` (ExerciseDB search by name/body part/target muscle/equipment — description spells out how each filter maps to a request, e.g. `equipment='dumbbell'` for equipment-constrained programs), `finalize_workout_plan` (emits structured workout_days/rest_days/notes; description requires exercise_id/exercise_name to trace back to a `search_exercises` result and equipment to respect any user-stated constraint).
- The system prompt asks the user about training days, equipment, and injuries before building a plan, instructs the agent to use real exercise IDs/names from `search_exercises`, and — like the meal agent — asks it to state its search intent in one sentence before each `search_exercises` call.

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

### Running the tests
The `tests/` package is a stdlib `unittest` suite — fast, deterministic, and
**no API calls** (unlike the live eval harness in `evals/`). `tests/test_grocery.py`
covers `generate_grocery_list`'s summing, discrete-unit rounding, and
store-section categorization, feeding `canonical_name` directly on each
ingredient (normalization itself is the LLM-backed `grocery_agent`, covered by
`evals/grocery_normalization.py` instead, since it needs real API calls). Run
from the repo root:
```bash
source venv/bin/activate
python -m unittest discover tests      # all unit tests
python -m unittest tests.test_grocery  # just the grocery list generation tests
```

### Debugging: checking which agent handled a turn
Query `agent_runs` directly to see what the coordinator decided:
```bash
psql franky_fitness -c "SELECT id, agent_type, user_id, created_at FROM agent_runs ORDER BY id DESC LIMIT 6;"
```
A successful turn inserts **two rows** with the same `created_at`: `coordinator` (the routing call) followed by `meal_agent` or `exercise_agent` (the specialist that handled it).

**Caveat:** `agent_runs` only gets written on a fully successful turn. Two cases write nothing:
- The grocery-list short-circuit ("grocery list" / "shopping list" in the message) — pure code, never reaches the coordinator, UNLESS it's the first grocery-list request for that plan, in which case it logs up to two extra rows (`agent_invoked = NULL`): a `grocery_normalizer` row on a name-normalization cache miss, and a `grocery_reconciler` row the first time that plan's ingredients get unit/category reconciliation.
- A failed coordinator/specialist call (`RuntimeError` → HTTP 502) — the exception is raised before the insert.

So "no new rows after sending a message" means either it hit the grocery shortcut with a fully-cached plan, or the request errored — check `/tmp/uvicorn.log` or the browser's network tab for a non-200 response.

### How transcripts and the eval harness work
- `backend/transcripts.build_transcript(...)` assembles a `Transcript` dict (`transcript_id`, `created_at`, `agent_type`, `agent_invoked`, `model`, `system`, `inputs`, `messages`, `steps`, `output`, `outcome`, `usage`, `latency_ms`) from an agent call's system prompt, input messages, and final history. `serialize_messages` converts Anthropic SDK content blocks (text/tool_use/tool_result) to JSON-safe dicts; `extract_steps` pairs each `tool_use` with its `tool_result` by `tool_use_id` (a `tool_use` with no result — e.g. the coordinator's forced `route` call — becomes a step with `result=None`).
- `run_meal_agent`/`run_exercise_agent` return a `transcript` alongside their existing fields; `coordinator._route` builds its own transcript for the routing call, and `run_coordinator` sets `agent_invoked` on both transcripts and includes them in each `agent_runs` entry.
- `/api/chat` calls `write_transcript(transcript)` for each `agent_runs` entry (appends to `transcripts/<date>.jsonl`) and stores `agent_invoked`/`transcript_id` on the corresponding `agent_runs` row — `agent_runs` is a queryable index only; **no prompt content lives in Postgres**.
- `python -m backend.view_transcript --last N` (optionally `--agent`/`--invoked`/`--id`/`--dir`) pretty-prints transcripts: system prompt, every message (including tool_use/tool_result), extracted tool calls, final output, outcome, usage, latency.
- `evals/tasks.py` holds the seed `TASKS` list (`meal_high_protein`, `meal_vegetarian_compliance`, `exercise_dumbbell_only`, `routing_recipe_howto`, `routing_workout_split`, `clarify_before_plan`, `no_invented_macros`) — each a `{id, description, inputs, profile, current_meal_plan, current_workout_plan, success_criteria, graders, source}` dict.
- `evals/graders.py` provides graders — `(transcript) -> {assertion, passed, reasoning}` — that read only `transcript["outcome"]`/`transcript["agent_invoked"]`/`transcript["steps"]`, never the live tool-call path. `judge(rubric)` is the LLM-as-judge grader (forced tool call on Haiku).
- `python -m evals.harness --trials N [--task ID]` runs each task `N` times via `run_coordinator()` (DB-free, fresh synthetic profile + inputs per trial), grades each trial, reports pass@N/pass^N per task and overall, and writes every trial's Transcript to `evals/results/<timestamp>/<task_id>-trial<n>.jsonl` (gitignored). **Makes real Anthropic + Spoonacular/ExerciseDB calls — keep `--trials` small.**
- See `evals/README.md` for how to add a new task from a real captured transcript (via `promote_to_task`).
- `backend/grocery_agent.normalize_ingredients` builds a `Transcript` with `agent_type="grocery_normalizer"` and `agent_invoked=None`, but only on a cache miss — `build_transcript`/`write_transcript` are the same functions used by the live agents, so these show up in `transcripts/<date>.jsonl` and are viewable via `view_transcript` like any other. `backend/grocery_agent.reconcile_quantities` builds a similar `Transcript` with `agent_type="grocery_reconciler"`, always (it's uncached — runs once per plan, persisted onto `plans.content`). `python -m evals.grocery_normalization` is a separate, smaller eval that exercises both directly (not via `run_coordinator`/`evals.harness`).

## Decisions Made This Session
- **PostgreSQL from the start** (not SQLite) — matches the PRD target. Installed via `brew install postgresql@17`.
- **Session-cookie auth** (not JWT) — `users`/`profiles`/`sessions` tables, bcrypt password hashing, replacing hardcoded `profiles.py`.
- **Vertical slices over horizontal layers** — ship one feature through all layers at a time.

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
