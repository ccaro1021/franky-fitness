# Implementation Plan: Franky Fitness

> Living document. Lives in `docs/` alongside the PRD and is referenced from `CLAUDE.md` so Claude Code picks it up each session. Updated as decisions are made — see the Decision Log at the bottom. The full product vision is in `docs/franky-fitness-prd.md`; this plan is the *build path* and the record of judgment calls that the PRD doesn't make.

---

## 1. Goal & Scope

**Goal:** A conversational AI wellness assistant ("Franky") for **Chris and Kaitlyn** — a web app where each person chats with Franky to get personalized weekly meal plans, grocery lists, and exercise plans, and where Franky improves over time by learning from their feedback. Facts (recipes, macros, exercises) come from real APIs; the model supplies judgment (selection, sequencing, coaching).

**A Tuesday that works:** Chris opens the app, asks "what's for dinner this week?", gets a 7-day plan he'd actually cook, asks "how do I make Thursday's salmon?", sees a recipe card, then generates the grocery list for the week. Kaitlyn does the same against her own profile and history.

**Non-goals (deferred or out of scope):**
- No social features (sharing, following, community plans).
- No third-party integrations (wearables, grocery delivery, calendar).
- No tracking of *actual* consumption or workouts performed — Franky generates plans, it does not log execution.
- No progress charts (weight trends, strength curves, body composition).
- No notifications/reminders, no image features (meal photos, barcode scan), no native mobile (responsive web only).
- No medical nutrition therapy — Franky flags medical mentions with a "consult a clinician" note and never diagnoses or prescribes.

---

## 2. Architecture & Key Decisions

The structural decisions that shape everything else. Each names the rejected alternative — if it doesn't, it's an assumption, not a decision.

> **Decision 1: Facts from APIs, judgment from the model**
> - **Choice:** Recipes/macros come from Spoonacular and exercises from ExerciseDB via tool calls. The agent selects, sequences, and coaches over real data — it never invents a recipe name, calorie count, or exercise.
> - **Alternative considered:** Let the model generate recipes and macros from training knowledge.
> - **Why:** Hallucinated nutrition data is worse than none; lookups are cheap and repeatable; and it makes output *checkable* — every meal in a plan traces to a real Spoonacular ID.
> - **Revisit if:** API coverage proves too narrow and plan variety suffers more than hallucination would cost.

> **Decision 2: Vertical slices over horizontal layers**
> - **Choice:** Ship one feature through every layer (agent → API → UI → persistence) before starting the next. Slice 1 = meal planning end-to-end; Slice 2 = recipe retrieval.
> - **Alternative considered:** Build all of the backend, then all of the frontend.
> - **Why:** Each slice is runnable and demoable; the architecture gets proven early on something real; direction is cheap to change between slices.
> - **Revisit if:** A slice needs so much shared infrastructure that building a layer first is genuinely cheaper.

> **Decision 3: Coordinator router over a monolithic agent — two specialists, not three**
> - **Choice:** A coordinator receives conversational input and routes to one of two LLM specialists — meal planning (which also covers nutrition guidance) and exercise. Grocery list generation is **not a third specialist**: summing ingredient quantities and categorizing by store section remain a deterministic code transform (`grocery.py`) of a saved meal plan. The coordinator (`backend/coordinator.py`) classifies the latest user message via a Haiku call with a forced `route` tool call (`tool_choice={"type": "tool", "name": "route"}`, enum `["meal", "exercise"]`), then dispatches to `run_meal_agent` or `run_exercise_agent` with the same conversation history. Ambiguous/general messages default to "meal".
> - **Alternative considered:** The PRD's original three-specialist split (meal, grocery, exercise) with a grocery LLM agent; a separate "nutrition verification" agent that reviews the meal agent's output before it's finalized; keyword-based routing; a separate endpoint/UI per specialist; an explicit UI mode toggle.
> - **Why:** Grocery list generation is arithmetic + categorization over data the meal plan already contains — no judgment is required, so an LLM call would add cost, latency, and hallucination risk for zero benefit. A separate nutrition pass is similarly redundant: the meal agent already has per-meal macros from Spoonacular in context and can reason over them directly (e.g., "this week is light on protein at breakfast") in the same call that builds the plan. A real LLM-based router (vs. keyword matching or a UI toggle) was chosen explicitly because a goal of this project is learning multi-agent system design — this is the PRD's coordinator pattern, just narrowed to two specialists.
> - **Revisit if:** Grocery categorization needs judgment a static ingredient-name lookup can't handle (ambiguous items, regional naming), or nutrition guidance needs to cross-reference data the meal agent doesn't already have in context — at that point a code lookup table or a second pass becomes worth the cost. Also revisit routing if single-message classification proves too coarse (e.g. follow-ups like "make day 3 harder" lose context about which plan they refer to) — at that point pass more conversation history or track the last-active specialist.
> - **Diverges from PRD:** The PRD (§AI Architecture) specifies a coordinator routing to three sub-agents including a grocery list agent. This plan deliberately narrows that to two LLM specialists plus a code-based grocery transform — noted here as a knowing divergence, same as the no-auth decision above.
> - **Note:** the router call needs `max_tokens` high enough (200) for Haiku to emit the forced tool call's JSON input — at `max_tokens=20` it returned an empty `input: {}` and silently fell back to the "meal" default with no error.
> - **2026-06-15 revision — the "Revisit if" trigger was hit:** the static `_INGREDIENT_ALIASES` lookup table couldn't keep pace with Spoonacular's long-tail ingredient phrasing (confirmed via a three-commit audit that still left real gaps). **Ingredient *normalization* (raw recipe phrasing → purchasable base item) becomes a single-batch LLM call** (`backend/grocery_agent.py`, NOT a tool-use agent), backed by a global, LLM-populated cache table seeded from the audited alias table. **Summing, rounding, and store-section categorization remain pure code in `grocery.py`, unchanged** — Decision 3's original rationale for *that* part still holds; only the naming-judgment piece moved to an LLM. See [`SLICE_9_GROCERY_AGENT_PLAN.md`](SLICE_9_GROCERY_AGENT_PLAN.md) and the decision log entry below.

> **Decision 4: Structured output via tool calls, not JSON mode**
> - **Choice:** Agents emit structured data by *calling a tool* (`finalize_meal_plan`, `get_recipe`). `_run_tool` returns a `(text_for_agent, structured_data_for_frontend)` tuple; the structured half is surfaced through the API response alongside the agent's prose.
> - **Alternative considered:** Force a single JSON response and parse it.
> - **Why:** Lets Franky *talk* to the user and *emit structured data* in the same turn — the chat stays conversational while the UI gets a typed payload to render as a card. Also keeps the tool-use loop uniform.
> - **Revisit if:** We need a structured artifact with zero accompanying chat, where a forced-JSON call would be simpler.

> **Decision 5: Personalization by prompt injection, not fine-tuning**
> - **Choice:** Before each agent call, inject the person's profile + their most recent saved plan + (future) a distilled preference summary into the system prompt. The model is never fine-tuned.
> - **Alternative considered:** Fine-tune on user history; or inject the full raw feedback table every call.
> - **Why:** Injection is immediate, debuggable, and free of training infra. A *distilled* summary (not raw feedback) keeps token cost flat as history grows — the raw `feedback` table exists to derive the summary, not for direct injection.
> - **Revisit if:** Preference summaries stop capturing enough nuance and per-meal feedback needs to be injected directly.

> **Decision 6: PostgreSQL from day one**
> - **Choice:** Local PostgreSQL 17 (`franky_fitness` db), `psycopg2` driver, raw SQL.
> - **Alternative considered:** SQLite now, migrate later.
> - **Why:** Matches the PRD's target and the JSONB columns we lean on for `content`; avoids a migration later. Setup cost was a one-time `brew install`.
> - **Revisit if:** We need to ship something portable with zero infra, where SQLite's single-file story wins.

> **Decision 7: Conversation history is frontend-only; context is injected fresh**
> - **Choice:** The messages list lives in React session state for the life of a conversation and is *not* persisted. Profile + saved plan are injected fresh into the system prompt on every `/api/chat` call.
> - **Alternative considered:** Persist conversation history server-side and rely on it for personalization.
> - **Why:** Personalization comes from durable structured context (profile, plans, preferences), not from chat transcript. Starting a new conversation cleanly resets without touching the DB. Keeps the chat endpoint stateless.
> - **Revisit if:** We want resumable conversations across sessions/devices.

---

## 3. Data Model & Contracts

The *shapes* that move between components. Once two components agree on a contract they can be built and tested independently.

### 3.1 Persisted tables

**Exists today** (`backend/database.py`):
- **users:** id, email (unique), password_hash, name, created_at
- **profiles:** user_id (PK, FK→users), height_inches, weight_lbs, target_weight_lbs, dietary_restrictions (JSONB), fitness_goals (JSONB), notes, updated_at — BMI is computed on the fly (`backend/users.compute_bmi`), not stored
- **sessions:** token (PK), user_id (FK→users), expires_at, created_at — session-cookie auth
- **plans:** id, user_id (FK→users), type (`meal_plan` | `grocery_list` | `workout_plan`), content (JSONB), created_at
- **agent_runs:** id, agent_type, user_id (FK→users), input_tokens, output_tokens, latency_ms, created_at
- **feedback:** id, user_id (FK→users), plan_id (FK to plans, nullable), item_type (`meal`|`exercise`), item_name, rating (`positive`|`negative`), note (nullable), created_at
- **preference_summaries:** user_id (PK, FK→users), summary (JSONB: liked_meals/disliked_meals/liked_workouts/disliked_workouts/patterns), updated_at

### 3.2 Tool contracts (the empty/error case is part of the contract)

| Tool | In | Out |
|---|---|---|
| `search_meals` *(exists)* | query (req), max_calories, min_protein, number | list of meal lines incl. Spoonacular ID + macros; **empty → "No recipes found"** so the agent relaxes filters, doesn't invent |
| `get_recipe` *(exists)* | spoonacular_id **or** meal_name (fallback) | text (ingredients+steps) for the agent **and** structured recipe for the UI; **failure → "Could not retrieve recipe"** |
| `finalize_meal_plan` *(exists)* | meals[] (day, meal_type, name, macros, spoonacular_id), notes | ack string; the input *is* the structured plan surfaced to the UI |
| `search_exercises` *(exists)* | name, body_part, target_muscle, equipment, limit | exercise records incl. ID, target muscle, equipment, secondary muscles; **empty → "No exercises found"** |
| `finalize_workout_plan` *(exists)* | workout_days[] (day, focus, exercises[] with exercise_id/exercise_name/sets/reps/rest_seconds), rest_days[], notes | ack string; the input *is* the structured plan surfaced to the UI |
| `route` *(exists, coordinator)* | latest user message | `agent` ∈ {meal, exercise} via forced tool call |

> **Grocery list is not a tool/agent call.** It's a plain Python function over a saved meal plan's ingredients (sum quantities by name+unit, map each name to a store-section category via a static lookup). See `grocery.py` in Component Breakdown.

> **Feedback is also not a tool/agent call.** `POST /api/feedback` (item_type, item_name, rating, note) is recorded directly via `backend/preferences.py`, which recomputes a `preference_summaries` row in pure code. See Decision Log entry for 2026-06-10 (Slice 5).

### 3.3 Agent envelopes

- **Coordinator → specialist:** the full conversation history (unchanged), plus that specialist's own context injection — meal agent gets the saved `meal_plan`, exercise agent gets the saved `workout_plan`. Both also get the user's profile (restrictions, goals, notes, and — when set — height/weight/target weight/BMI).
- **Specialist → coordinator → API:** prose message + optional structured artifact (`meal_plan` | `recipe` | `grocery_list` | `workout_plan`), each null unless that turn produced it. `run_coordinator` also returns `agent_runs`: a list of `{agent_type, input_tokens, output_tokens, latency_ms}` — one entry for the routing call (`agent_type="coordinator"`) and one for whichever specialist ran — both logged to `agent_runs`.

### 3.4 Output schemas the user sees
- **MealPlan:** meals grouped by day → meal_type, with per-meal macros (rendered by `MealPlanCard`).
- **Recipe:** name, per-serving macros, ingredients[], numbered steps (rendered by `RecipeCard`).
- **GroceryList:** items[] with {name, total_quantity, unit, category}, category ∈ {produce, protein, dairy, pantry, frozen} (rendered by `GroceryListCard`).
- **WorkoutPlan:** workout_days[] → {day, focus, exercises[] (exercise_id, exercise_name, sets, reps, rest_seconds)}, rest_days[], notes (rendered by `WorkoutPlanCard`).

---

## 4. Component Breakdown

| Component | One job | Depends on |
|---|---|---|
| `spoonacular.py` *(exists)* | Fetch recipes/macros/ingredients from Spoonacular | API key |
| `exercisedb.py` *(exists)* | Fetch exercises from ExerciseDB | API key |
| `backend/auth.py` *(exists)* | Password hashing, session create/lookup/delete, `get_current_user` dependency | bcrypt, sessions table |
| `backend/users.py` *(exists)* | User + profile CRUD, BMI computation, builds the profile context injected into agent prompts | users/profiles tables |
| `backend/database.py` *(exists)* | Postgres connection + table setup | DATABASE_URL |
| `backend/meal_agent.py` *(exists)* | Produce meal plans & recipes via tool-use loop over Spoonacular | spoonacular, profile context, plan context |
| `backend/exercise_agent.py` *(exists)* | Produce workout plans via tool-use loop over ExerciseDB | exercisedb, profile context, plan context |
| `backend/coordinator.py` *(exists)* | Classify each turn (Haiku, forced `route` tool call) and dispatch to meal or exercise specialist | meal_agent, exercise_agent |
| `grocery.py` *(exists)* | Pure code: sum ingredient quantities across a meal plan and categorize by store section (no LLM call) | a saved meal plan, static category lookup |
| `backend/main.py` *(exists)* | HTTP routes; auth/profile endpoints; inject saved meal/workout plan context; log agent_runs for coordinator + specialist | coordinator, database, auth, users |
| `frontend/` Chat + cards + AuthPage + ProfilePage *(exists)* | Render the conversation, structured artifacts (meal plan, recipe, grocery list, workout plan), login/signup, and profile editing | backend API |
| `backend/preferences.py` *(exists)* | Pure code: record feedback rows and recompute the per-user preference summary (no LLM call) | feedback table |

**Entry points:** backend `uvicorn backend.main:app`; frontend `npm run dev` (Vite proxies `/api` → `:8000`).

---

## 5. Build Order

Dependencies first, scariest unknowns early, each step ends in something runnable.

1. ☑ **Meal planning end-to-end** *(Slice 1)* — proves the whole stack: agent tool-loop → API → React card → Postgres save.
2. ☑ **Recipe retrieval** *(Slice 2)* — injects the saved plan into the prompt; `get_recipe` resolves a meal to its ID and renders a `RecipeCard`. Proves plan-as-context.
3. ☑ **Grocery list from a saved meal plan** *(Slice 3)* — *pure code (`grocery.py`): sum ingredient quantities across the week's meals and categorize by store section via a static lookup. No new agent, no LLM call.*
4. ☑ **Exercise agent + coordinator routing** *(Slice 4)* — *`backend/exercise_agent.py` ports the workout logic from `franky.py`/`exercisedb.py` into the web app as the second LLM specialist; `backend/coordinator.py` adds a Haiku-based router (forced `route` tool call) that classifies each turn and dispatches to meal or exercise. `WorkoutPlanCard` renders the result; workout plans persist as `type='workout_plan'` rows.*
5. ☑ **Feedback + preference summaries** *(Slice 5)* — *thumbs up/down (+ optional note) on saved meals/exercises via `FeedbackButtons`, recorded through `POST /api/feedback`. `backend/preferences.py` recomputes a per-person summary in pure code (most-recent rating per item wins) and `/api/chat` injects it into both specialists' system prompts.*
6. ☑ **Auth + profiles table** *(Slice 6)* — *replaced hardcoded `profiles.py` with `users`/`profiles`/`sessions` tables, session-cookie auth, and a Profile page (height/weight/target weight/goals/restrictions, BMI computed on the fly). `person_name` strings fully replaced with `user_id` FKs across plans/agent_runs/feedback/preference_summaries.*
7. ☑ **View/correct preference summary** *(Slice 7, PRD stories 63-64)* — *`GET /api/preferences` surfaces the `preference_summaries` row; the Profile page renders liked/disliked meals and exercises as removable tags. `backend/preferences.forget_item` deletes the underlying `feedback` rows for an `(item_type, item_name)` and recomputes the summary, so removing a tag is a real correction, not just a UI hide.*
8. ☑ **Transcript observability + eval harness** *(Slice 8)* — *full execution spec in [`SLICE_8_OBSERVABILITY_EVALS_PLAN.md`](SLICE_8_OBSERVABILITY_EVALS_PLAN.md). Phase 1: `backend/transcripts.py` builds a canonical `Transcript` (system prompt, messages, tool calls/results, output, outcome, tokens/latency, `agent_invoked`) for every agent call; each is appended to gitignored `transcripts/<date>.jsonl`. `agent_runs` is demoted to a queryable index (`+agent_invoked`, `+transcript_id`; no prompt content in the DB). `backend/view_transcript.py` is a CLI to read them (`--last`, `--agent`, `--invoked`, `--id`). Phase 2: `evals/` harness (`tasks.py`/`graders.py`/`harness.py`) replays a 7-task seed set through `run_coordinator` (DB-free) for k trials, grades each Transcript's `outcome`/`agent_invoked` with code-based + LLM-as-judge graders, and reports pass@k/pass^k — `python -m evals.harness --trials 3`.*

**Riskiest assumption, tested earliest:** that an agent plans *well* over API lookups (not just *runs*). Slices 1–2 already exercise this; the eval suite (§7) is what turns "seems fine" into "passes."

---

## 6. Risks & Open Questions

- **Open — recipe IDs in plans:** `finalize_meal_plan` trusts the agent to carry the `spoonacular_id` from `search_meals` results into the plan. If it drops or fabricates one, `get_recipe` falls back to name search. *Mitigation candidate: validate every `spoonacular_id` in a finalized plan against what was actually returned by search. Deferring until we see how often IDs go missing in real use.*
- **Risk — Spoonacular free-tier limits.** Heavy plan generation could hit daily caps. *Mitigation: cache resolved recipes; consider a one-time ingest of a recipe store (mirroring the facts-from-data decision) if limits bite.*
- **Risk — preference-summary token growth.** Injecting history every call grows cost. *Mitigation is already the design (Decision 5): inject the distilled summary, never the raw feedback table. Worth measuring once feedback exists.*
- **Risk — multi-agent latency.** Coordinator + specialist + tool calls compound latency. *Turn this into a measured eval, not an assertion — `agent_runs` already logs latency_ms per call.*
- **Assumption — two people, one app, separate contexts is enough.** Each login swaps profile + plan context. If Chris and Kaitlyn ever need a *shared* plan ("plan dinners we both eat"), the per-user model needs rethinking. *Out of scope for now (PRD: no household accounts), but the most likely thing to force a restructure.*

---

## 7. Success Criteria

Every criterion is checkable — by code, by a model grading a transcript, or by eyeballing against a written standard.

**Meal agent passes when:**
- Output matches the MealPlan schema; every meal has day, meal_type, name, and all four macros — *code check*
- Every `spoonacular_id` present in a plan was returned by a `search_meals` call in that session — *code check*
- No meal violates the person's stated dietary restrictions — *model-graded check*
- A 7-day request yields 7 distinct days, not a repeated template — *code check*

**Recipe retrieval passes when:**
- Asking "how do I make [meal] from my plan" returns a recipe whose name matches a meal in the saved plan, with non-empty ingredients and steps — *code + model-graded*

**Grocery list generation passes when** *(its slice):* every meal-plan ingredient appears; duplicates are consolidated with combined quantities; every item has a store-section category — *code check (no model grading needed — it's pure code)*

**Exercise agent passes when:** day count matches the request; each exercise has sets, reps/duration, and rest_seconds; every `exercise_id` in a finalized plan was returned by a `search_exercises` call in that session; flagged-injury exercises are absent — *code + model-graded*

**Coordinator passes when:** meal-related messages route to the meal agent and exercise-related messages route to the exercise agent; ambiguous/general messages don't crash either specialist — *model-graded check on a labeled set of sample messages*

**Regression / whole system:** run the eval suite (modeled on the existing `eval_franky.py` pattern) before exposing Franky to anyone beyond Chris & Kaitlyn. **Minimum bar: pass^3** (succeeds on all of 3 runs) on each agent's core behaviors — a product whose value is consistency can't ship on single-run luck.

**Whole system passes when:** Chris and Kaitlyn can each get a week's meals + grocery list + workout from one conversation against their own profile and history — and would actually follow it.

---

## Decision Log (append-only)

- **2026-06-08** — Chose a **vertical-slice** build order over horizontal layers; shipped Slice 1 (meal planning end-to-end).
- **2026-06-08** — **PostgreSQL from the start** over SQLite (matches PRD, uses JSONB, avoids a later migration). Installed via Homebrew `postgresql@17`.
- **2026-06-08** — **No auth in v1**; Chris & Kaitlyn hardcoded in `backend/profiles.py`. Single-household first, structured so auth slots in later. Knowingly diverges from the PRD's multi-user framing.
- **2026-06-08** — **Structured output via tool calls** (`_run_tool` returns `(text, data)`) so Franky talks and emits a typed UI payload in one turn.
- **2026-06-09** — Shipped Slice 2 (**recipe retrieval**): inject the most recent saved plan into the agent prompt each turn; `get_recipe` resolves a meal to its Spoonacular ID and the UI renders a `RecipeCard`. Confirmed the plan-as-context pattern that personalization (Decision 5) will build on.
- **2026-06-09** — **Dropped the grocery agent and a separate nutrition-verification agent.** Grocery list generation is pure code (`grocery.py`) — summing ingredient quantities and categorizing by store section needs no model judgment. Nutrition guidance is handled by the meal agent directly, since it already has per-meal macros from Spoonacular in context. The system now has two LLM specialists (meal+nutrition, exercise) instead of the PRD's three. See revised Decision 3.
- **2026-06-09** — Shipped Slice 3 (**grocery list generation**): `finalize_meal_plan` now fetches and stores each meal's full ingredient list (one Spoonacular `get_recipe` call per meal with a known ID). `grocery.py` sums quantities and categorizes by store section via a static keyword lookup — pure code, no LLM. Triggered via a button on `MealPlanCard` (`GET /api/plans/{id}/grocery-list`) or by chat intent ("grocery list" / "shopping list" short-circuits `/api/chat` before the agent runs).
- **2026-06-10** — Shipped Slice 4 (**exercise agent + coordinator routing**): chose the real LLM-based coordinator (Option C) over keyword routing, a separate endpoint/UI, or a UI mode toggle, since a stated project goal is learning multi-agent system design. `backend/exercise_agent.py` mirrors `meal_agent.py` (search_exercises + finalize_workout_plan tools, profile + saved-workout-plan injection). `backend/coordinator.py` classifies the latest user message via Haiku with a forced `route` tool call and dispatches to meal or exercise. `/api/chat` now fetches both the latest meal_plan and workout_plan, logs one `agent_runs` row for the coordinator and one for the chosen specialist. `/api/plans` (POST/GET) generalized with a `type` field (`meal_plan` | `workout_plan`). New `WorkoutPlanCard` renders the plan with a Save button. **Caught during testing:** the router's `max_tokens=20` was too small for Haiku to emit the forced tool call's input — it returned `{}` and silently defaulted to "meal" with no error. Fixed by raising `max_tokens` to 200.
- **2026-06-10** — Shipped Slice 5 (**feedback + preference summaries**): saved `MealPlanCard`/`WorkoutPlanCard` rows now have 👍/👎 `FeedbackButtons` (with an optional note) calling `POST /api/feedback`. `backend/preferences.py` is **pure code** (Decision 3 precedent) — it inserts into `feedback` and recomputes `preference_summaries` by taking the most-recent rating per `(item_type, item_name)` and bucketing into `liked_meals`/`disliked_meals`/`liked_workouts`/`disliked_workouts`. `/api/chat` fetches this summary and threads it through `run_coordinator` to whichever specialist runs; both agents append a "Known preferences" block to their system prompt when any bucket is non-empty. **Two deliberate scope cuts:** (1) the PRD's `patterns: []` field is left empty — deriving free-text patterns needs model judgment, deferred until there's a concrete reason to add an LLM call here; (2) no "view/correct my preferences" UI yet (PRD stories 63-64) — feedback collection and prompt injection only. **Diverges from the PRD's `plan_items` table:** plans remain a single JSONB blob; feedback is keyed by `(person_name, item_type, item_name)` plus an optional `plan_id` for traceability, since the dish/exercise name — not a row ID — is what's useful for "don't suggest this again."
- **2026-06-10** — Shipped Slice 6 (**auth + user profiles**): replaced hardcoded `backend/profiles.py` with real accounts. **Auth:** session-cookie + DB-backed `sessions` table (not JWT) — simple, revocable on logout, and the Vite dev proxy makes `/api/*` same-origin so cookies need no special CORS handling beyond `allow_credentials=True`. Passwords hashed with `bcrypt` (`backend/auth.py`); `get_current_user` is a FastAPI dependency reading the `session_token` cookie. **Profiles:** new `profiles` table holds height_inches/weight_lbs/target_weight_lbs/dietary_restrictions/fitness_goals/notes; BMI is computed on the fly (`backend/users.compute_bmi`), never stored, since it's derived and would go stale. Both agents' system prompts now include a "stats" block (height/weight/target/BMI) when those fields are set, alongside the existing dietary-restrictions/goals/notes block. **Onboarding:** minimal signup (email/password/name) plus a separate Profile page (`ProfilePage.jsx`) for height/weight/target/goals/restrictions — chosen over a multi-step onboarding wizard since the data can be filled in incrementally. **Migration:** `backend/migrate_to_auth.py` is a one-time interactive script (run manually, prompts for Chris & Kaitlyn's email/password via `getpass`) that creates their `users`/`profiles` rows seeded from the old `PROFILES` dict, then backfills and fully replaces `person_name` with `user_id` across `plans`/`agent_runs`/`feedback`/`preference_summaries` (including moving `preference_summaries`'s primary key from `person_name` to `user_id`) and drops the old column — chosen over keeping both columns indefinitely, since a clean cutover avoids two parallel identity systems. The person-selector UI is gone; `App.jsx` now gates on `GET /api/auth/me` and shows `AuthPage` (login/signup) or the chat + profile views.
- **2026-06-10** — Shipped Slice 7 (**view/correct preference summary**, PRD stories 63-64): `GET /api/preferences` returns the user's `preference_summaries` row, falling back to a new `EMPTY_SUMMARY` constant (all buckets empty) if no feedback has been recorded yet. `ProfilePage` adds a "What Franky Knows About You" section listing `liked_meals`/`disliked_meals`/`liked_workouts`/`disliked_workouts` as removable tags. **Correction mechanism:** rather than letting the summary itself be hand-edited (which `_recompute_summary` would silently overwrite on the next feedback submission), removing a tag calls `POST /api/preferences/forget`, which deletes that user's `feedback` rows for the `(item_type, item_name)` and recomputes the summary — so a corrected item stays gone unless the user re-rates it. The `patterns` field remains an empty array (still deferred, per Slice 5).
- **2026-06-12** — **Shipped Slice 8 (transcript observability + eval harness)** — full spec in [`SLICE_8_OBSERVABILITY_EVALS_PLAN.md`](SLICE_8_OBSERVABILITY_EVALS_PLAN.md). Driven by two user asks: (1) easily access the prompt/output/tool-calls/agent-invoked for any turn, and (2) run evals per Anthropic's *"Demystifying Evals for AI Agents"*. **Key decisions made during design:** (a) **One `Transcript` schema, identical for live turns and eval trials** — because the article's core workflow is mining production traces into eval cases, so a captured failure becomes a regression test by copy, not transform. (b) **JSONL files are the canonical store; `agent_runs` is demoted to a queryable index** (adds `agent_invoked`, `transcript_id`; deliberately stores **no prompt content** — keeps health data out of Postgres and stays portable to Braintrust/Langfuse/Phoenix later, per the article's "pick a framework, don't over-invest in harness infra"). This was chosen over the earlier draft that put full prompts in an `agent_runs` JSONB column, after explicitly checking which option mapped best to the article (the article is DB-vs-file agnostic but centers on a single portable trace/dataset format that bridges observability and eval datasets). (c) **Home-grown minimal harness** over adopting a framework now, consistent with the project's learning goal and the Decision-3 pure-code precedent. (d) Tasks seeded from **the project's own real failures** (e.g. the `max_tokens=20` router bug, `search_meals` API-failure handling) per the article's "start with real failures," graded with **code-based graders preferred, LLM-as-judge only where necessary**, reporting **pass@k and pass^k** (k=3 → the PRD's pass^3). **Considered but rejected:** switching to the Anthropic Agent SDK as the vehicle for this — it provides cleaner injection points (hooks/message stream) but would NOT hand you a prompt/response log for free (you still serialize it yourself), and the current hand-rolled loop already has the exact `system`/`history`/response objects in hand, so the SDK buys nothing for this specific need and isn't worth a 3-file rewrite of working agents.
- **2026-06-12** — **Built and verified Slice 8.** Phase 1: `backend/transcripts.py` (`serialize_messages`/`extract_steps`/`build_transcript`/`write_transcript`/`read_transcripts`/`promote_to_task`), wired into `meal_agent.run_meal_agent`, `exercise_agent.run_exercise_agent`, and `coordinator._route`/`run_coordinator` (which attaches `agent_invoked` to both the coordinator and specialist transcripts). `agent_runs` gained `agent_invoked`/`transcript_id` via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. `backend/main.py` writes each turn's transcripts to gitignored `transcripts/<date>.jsonl` and stores the pointer columns. `backend/view_transcript.py` supports `--last`/`--agent`/`--invoked`/`--id`/`--dir`. Verified end-to-end via the live API: two transcripts per turn, correct `agent_invoked`, no prompt content in Postgres. **One refinement during 1b:** `extract_steps` originally only emitted a step when a `tool_use` had a matching `tool_result`; the coordinator's forced `route` call never gets a `tool_result`, so unmatched `tool_use` blocks now become steps with `result=None`. Phase 2: `evals/tasks.py` (7-task seed set), `evals/graders.py` (`routed_to`, `plan_has_n_days`, `every_meal_min_protein` with an optional `meal_types` filter, `no_restricted_ingredients`, `equipment_subset`, `emitted_no_plan`, `macros_trace_to_search`, `judge`), `evals/harness.py` (`python -m evals.harness --trials N [--task ID]`), `evals/README.md`. **Findings from running the harness during verification (left as-is — real signal for the regression set, not bugs in the harness):** `clarify_before_plan` fails because the meal agent asks ~3 clarifying questions instead of the prompt's "one focused question at a time"; `meal_high_protein` sometimes fails because breakfast suggestions from `search_meals` come back under 30g protein (the `every_meal_min_protein` grader gained a `meal_types` filter so it can target breakfast/lunch/dinner specifically); `meal_vegetarian_compliance` hit a real Spoonacular rate-limit during this session, which the meal agent correctly handled by refusing to invent data rather than fabricating a plan. These are good Slice 9 candidates (prompt tuning + API-failure resilience).
- **2026-06-13** — **Aligned `meal_agent.py`/`exercise_agent.py` to Anthropic's "Building Effective Agents."** Three changes, scoped down from a broader list via user choice: (1) **`MAX_TURNS = 10` guardrail** on both agents' tool-use `while` loops — if hit, the loop breaks with a fallback "too much back-and-forth" message and `outcome["hit_max_turns"] = True`, addressing the article's warning about error-compounding in unbounded agentic loops. (2) **Tightened tool descriptions (ACI)** — `search_meals`/`get_recipe` and `search_exercises`/`finalize_workout_plan` now spell out boundaries (e.g. `get_recipe` is ONLY for explicit "how do I make X" requests, never during plan-building; `finalize_meal_plan` fetches ingredients automatically so the agent shouldn't supply them) and give concrete example inputs per filter. (3) **Plan-then-act transparency** — both system prompts now ask the agent to state in one sentence what it's about to search for and why before each search call; these intermediate text blocks are captured for free by the existing `serialize_messages`/`extract_steps` transcript pipeline, no harness changes needed. **Verified via `python -m evals.harness`:** ran the full suite at `--trials 1` (4/7 pass; `MAX_TURNS` never triggered) and `meal_high_protein` at `--trials 3` both with and without these changes (stash/pop) — identical pass@3=100%/pass^3=0% pattern on unmodified `main`, confirming the `meal_high_protein`/`meal_vegetarian_compliance`/`exercise_dumbbell_only` flakiness noted in the prior entry is **pure model sampling variance** (same prompt, different decisions to ask a clarifying question vs. build the plan, and protein values landing a few grams under 30g), not caused by or fixed by these prompt edits. Still a Slice 9 candidate.
- **2026-06-15** — **Maintenance + Slice 9 design.** (1) Flattened `.claude/skills/` (Claude Code only discovers skills one level deep; they'd been nested under `engineering/`/`productivity/` category folders from the source repo). (2) Expanded then audited `grocery.py`'s `_INGREDIENT_ALIASES` (~89 entries) to stop over-collapsing distinctions that change what's actually purchased — bell-pepper colors, fresh vs. dried herbs, ground vs. fresh ginger, salted/unsalted butter, shredded/grated cheese forms, "boneless skinless", minced garlic, Greek yogurt, heavy cream all kept distinct. Added the project's first unit test suite, `tests/test_grocery.py` (stdlib `unittest`, no API calls, 17 tests), covering the alias table via `generate_grocery_list`. (3) **Designed Slice 9 (grocery normalization agent)** via a `/grill-me` session, prompted by "the alias table isn't working" — converting recipe ingredient phrasing to purchasable items is fundamentally a judgment call a static dict can't generalize. **This revises Decision 3** (see above) rather than reversing it: only the naming-normalization step becomes an LLM call (`backend/grocery_agent.py`, single batch call, NOT a tool-use agent), backed by a global cache table seeded from the just-audited alias table plus curated few-shot guidance encoding the audit's patterns (fresh/dried, color variants, cut descriptors, "prepared form ≠ raw form"). Summing/categorization stay in `grocery.py`, unchanged. Other decisions: ingredient fetching (`get_recipe`) moves from `finalize_meal_plan` to grocery-list-request time, fetching only meals still in the saved plan (saves Spoonacular calls on removed meals — meal removal itself is a separate future slice); results persist onto `plans.content` after first generation so repeat requests are pure code; failed `get_recipe`/cache-miss meals retry on the next request rather than caching a permanent failure; the normalizer call gets a `Transcript` (`agent_type="grocery_normalizer"`) since it's rare after the cache fills; **`claude-opus-*`** is the chosen model specifically because cache-miss calls are rare but their (wrong) output is cached forever. Full design in [`SLICE_9_GROCERY_AGENT_PLAN.md`](SLICE_9_GROCERY_AGENT_PLAN.md). Not yet built.
