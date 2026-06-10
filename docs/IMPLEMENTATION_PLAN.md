# Implementation Plan: Franky Fitness

> Living document. Lives in `docs/` alongside the PRD and is referenced from `CLAUDE.md` so Claude Code picks it up each session. Updated as decisions are made — see the Decision Log at the bottom. The full product vision is in `docs/franky-fitness-prd.md`; this plan is the *build path* and the record of judgment calls that the PRD doesn't make.

---

## 1. Goal & Scope

**Goal:** A conversational AI wellness assistant ("Franky") for **Chris and Kaitlyn** — a web app where each person chats with Franky to get personalized weekly meal plans, grocery lists, and exercise plans, and where Franky improves over time by learning from their feedback. Facts (recipes, macros, exercises) come from real APIs; the model supplies judgment (selection, sequencing, coaching).

**A Tuesday that works:** Chris opens the app, asks "what's for dinner this week?", gets a 7-day plan he'd actually cook, asks "how do I make Thursday's salmon?", sees a recipe card, then generates the grocery list for the week. Kaitlyn does the same against her own profile and history.

**Non-goals (deferred or out of scope):**
- **Auth / multi-user accounts — deferred, not never.** v1 has no login; Chris & Kaitlyn are hardcoded profiles (`backend/profiles.py`). The schema and API are structured so email/password auth can slot in later without a rewrite. *This is the one place we knowingly diverge from the PRD's "multi-user product" framing — we build single-household first.*
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

> **Decision 3: Coordinator router over a monolithic agent**
> - **Choice:** A coordinator receives conversational input and routes to one of three specialists — meal, grocery, exercise. The grocery agent always receives a meal plan as input. (Today only the meal agent exists; the router is added when the second agent lands — see Build Order.)
> - **Alternative considered:** One agent with all tools and one giant system prompt.
> - **Why:** Smaller per-agent prompts behave more reliably; failures isolate and debug cleanly; the boundaries mirror how the domains actually differ (meals are daily-combinatorial, workouts are weekly-structural, grocery is a deterministic-ish transform of a meal plan).
> - **Revisit if:** Cross-domain features ("high-protein meals on lifting days") force so much handoff that the boundary costs more than it saves.

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
- **plans:** id, person_name, type (`meal_plan` | `grocery_list` | `workout_plan`), content (JSONB), created_at
- **agent_runs:** id, agent_type, person_name, input_tokens, output_tokens, latency_ms, created_at

**Planned** (from PRD §Data Models — add when their slice lands, not before):
- **users:** id, email, password_hash, name, created_at *(auth slice)*
- **profiles:** id, user_id (FK), height, weight, bmi, dietary_restrictions (JSON), fitness_goals (JSON), updated_at *(replaces hardcoded `profiles.py`)*
- **feedback:** id, person/user_id, plan_item_id, rating (`positive`|`negative`), note (nullable), created_at
- **preference_summaries:** id, user_id, summary (JSON: liked/disliked meals & workouts, patterns[]), updated_at

> **Migration note:** `plans.person_name` and `agent_runs.person_name` are string keys today because there are no user rows. When auth lands, these become `user_id` FKs. Keep this in mind before adding more `person_name`-keyed tables.

### 3.2 Tool contracts (the empty/error case is part of the contract)

| Tool | In | Out |
|---|---|---|
| `search_meals` *(exists)* | query (req), max_calories, min_protein, number | list of meal lines incl. Spoonacular ID + macros; **empty → "No recipes found"** so the agent relaxes filters, doesn't invent |
| `get_recipe` *(exists)* | spoonacular_id **or** meal_name (fallback) | text (ingredients+steps) for the agent **and** structured recipe for the UI; **failure → "Could not retrieve recipe"** |
| `finalize_meal_plan` *(exists)* | meals[] (day, meal_type, name, macros, spoonacular_id), notes | ack string; the input *is* the structured plan surfaced to the UI |
| `search_exercises` *(planned)* | name, body_part, target_muscle, equipment, limit | exercise records; empty → relax filters |
| `finalize_workout_plan` *(planned)* | workout_days[] (day, focus, exercises[]), rest_days[], notes | ack; input is the structured plan |
| `generate_grocery_list` *(planned)* | the structured meal plan | items[] grouped by store section, quantities consolidated |

### 3.3 Agent envelopes (when the coordinator exists)

- **Coordinator → specialist:** profile (restrictions, goals, BMI) + preference summary + conversational input. **Grocery agent additionally** receives the current structured meal plan.
- **Specialist → coordinator:** prose message + optional structured artifact (MealPlan | WorkoutPlan | GroceryList | Recipe), validated against its schema before returning to the frontend.

### 3.4 Output schemas the user sees
- **MealPlan:** meals grouped by day → meal_type, with per-meal macros (rendered by `MealPlanCard`).
- **Recipe:** name, per-serving macros, ingredients[], numbered steps (rendered by `RecipeCard`).
- **GroceryList** *(planned):* items[] with {name, total_quantity, unit, category}, category ∈ {produce, protein, dairy, pantry, frozen}.
- **WorkoutPlan** *(planned):* days[] → {focus, exercises[] (sets, reps/duration, RPE, rest)}, warm-up + cooldown per day.

---

## 4. Component Breakdown

| Component | One job | Depends on |
|---|---|---|
| `spoonacular.py` *(exists)* | Fetch recipes/macros/ingredients from Spoonacular | API key |
| `exercisedb.py` *(exists)* | Fetch exercises from ExerciseDB | API key |
| `backend/profiles.py` *(exists)* | Hold Chris & Kaitlyn's profile context (temporary stand-in for the profiles table) | — |
| `backend/database.py` *(exists)* | Postgres connection + table setup | DATABASE_URL |
| `backend/meal_agent.py` *(exists)* | Produce meal plans & recipes via tool-use loop over Spoonacular | spoonacular, profiles, plan context |
| `backend/main.py` *(exists)* | HTTP routes; inject saved-plan context; log agent_runs | meal_agent, database, profiles |
| `frontend/` Chat + cards *(exists)* | Render the conversation and structured artifacts; person selector | backend API |
| Coordinator *(planned)* | Route input to meal/grocery/exercise specialist | all agents |
| `grocery_agent.py` *(planned)* | Turn a meal plan into a consolidated, categorized list | a meal plan |
| `exercise_agent.py` *(planned)* | Produce workout plans over ExerciseDB | exercisedb, profiles |
| Feedback + preference summary *(planned)* | Store thumbs up/down; distill into a per-person summary | feedback table |

**Entry points:** backend `uvicorn backend.main:app`; frontend `npm run dev` (Vite proxies `/api` → `:8000`).

---

## 5. Build Order

Dependencies first, scariest unknowns early, each step ends in something runnable.

1. ☑ **Meal planning end-to-end** *(Slice 1)* — proves the whole stack: agent tool-loop → API → React card → Postgres save.
2. ☑ **Recipe retrieval** *(Slice 2)* — injects the saved plan into the prompt; `get_recipe` resolves a meal to its ID and renders a `RecipeCard`. Proves plan-as-context.
3. ☐ **Grocery list from a saved meal plan** — *reuses the proven pattern; the grocery agent consolidates quantities and categorizes by store section. First multi-agent handoff (meal plan → grocery).*
4. ☐ **Exercise agent** — *port the workout logic already prototyped in `franky.py`/`exercisedb.py` into the web app; second independent specialist.*
5. ☐ **Coordinator routing** — *only now is there more than one thing to route between; add the router and a single chat entry that dispatches by intent.*
6. ☐ **Feedback + preference summaries** — *thumbs up/down on meals/workouts → derive a per-person summary → inject it. Personalization comes after generic plans are solid.*
7. ☐ **Auth + profiles table** — *replace hardcoded `profiles.py` with users/profiles, swap `person_name` strings for `user_id` FKs. Last, because everything works single-household first.*

**Riskiest assumption, tested earliest:** that an agent plans *well* over API lookups (not just *runs*). Slices 1–2 already exercise this; the eval suite (§7) is what turns "seems fine" into "passes."

---

## 6. Risks & Open Questions

- **Open — recipe IDs in plans:** `finalize_meal_plan` trusts the agent to carry the `spoonacular_id` from `search_meals` results into the plan. If it drops or fabricates one, `get_recipe` falls back to name search. *Mitigation candidate: validate every `spoonacular_id` in a finalized plan against what was actually returned by search. Deferring until we see how often IDs go missing in real use.*
- **Open — when does auth land?** Everything is keyed on `person_name` strings. The longer we wait, the more tables inherit that key. *Decision deferred to Build Order step 7, but revisit immediately if a second household ever wants in.*
- **Risk — Spoonacular free-tier limits.** Heavy plan generation could hit daily caps. *Mitigation: cache resolved recipes; consider a one-time ingest of a recipe store (mirroring the facts-from-data decision) if limits bite.*
- **Risk — preference-summary token growth.** Injecting history every call grows cost. *Mitigation is already the design (Decision 5): inject the distilled summary, never the raw feedback table. Worth measuring once feedback exists.*
- **Risk — multi-agent latency.** Coordinator + specialist + tool calls compound latency. *Turn this into a measured eval, not an assertion — `agent_runs` already logs latency_ms per call.*
- **Assumption — two people, one app, separate contexts is enough.** The person selector swaps profile + plan context. If Chris and Kaitlyn ever need a *shared* plan ("plan dinners we both eat"), the per-person model needs rethinking. *Out of scope for now (PRD: no household accounts), but the most likely thing to force a restructure.*

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

**Grocery agent passes when** *(its slice):* every meal-plan ingredient appears; duplicates are consolidated with combined quantities; every item has a store-section category — *code check*

**Exercise agent passes when** *(its slice):* day count matches the request; each session has warm-up/work/cooldown; each exercise has sets, reps/duration, RPE; flagged-injury exercises are absent — *code + model-graded*

**Regression / whole system:** run the eval suite (modeled on the existing `eval_franky.py` pattern) before exposing Franky to anyone beyond Chris & Kaitlyn. **Minimum bar: pass^3** (succeeds on all of 3 runs) on each agent's core behaviors — a product whose value is consistency can't ship on single-run luck.

**Whole system passes when:** Chris and Kaitlyn can each get a week's meals + grocery list + workout from one conversation against their own profile and history — and would actually follow it.

---

## Decision Log (append-only)

- **2026-06-08** — Chose a **vertical-slice** build order over horizontal layers; shipped Slice 1 (meal planning end-to-end).
- **2026-06-08** — **PostgreSQL from the start** over SQLite (matches PRD, uses JSONB, avoids a later migration). Installed via Homebrew `postgresql@17`.
- **2026-06-08** — **No auth in v1**; Chris & Kaitlyn hardcoded in `backend/profiles.py`. Single-household first, structured so auth slots in later. Knowingly diverges from the PRD's multi-user framing.
- **2026-06-08** — **Structured output via tool calls** (`_run_tool` returns `(text, data)`) so Franky talks and emits a typed UI payload in one turn.
- **2026-06-09** — Shipped Slice 2 (**recipe retrieval**): inject the most recent saved plan into the agent prompt each turn; `get_recipe` resolves a meal to its Spoonacular ID and the UI renders a `RecipeCard`. Confirmed the plan-as-context pattern that personalization (Decision 5) will build on.
