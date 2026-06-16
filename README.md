# Franky Fitness

Franky is a conversational AI meal-planning, exercise, and grocery assistant built for a couple. You chat with Franky in plain language and get back structured weekly meal plans, workout programs, and an automatically-consolidated grocery list — all tailored to two people's profiles, goals, and dietary restrictions.

> **Live demo:** [franky-frontend-1097300861746.us-central1.run.app](https://franky-frontend-1097300861746.us-central1.run.app) &nbsp;·&nbsp; built with the Anthropic Python SDK, FastAPI, React, and PostgreSQL.

<!-- TODO: add a screenshot or short GIF of the chat → meal plan → grocery list flow here -->

## What it does

- **Conversational planning.** Ask for "a high-protein week for two" or "a 3-day dumbbell-only split" and Franky builds a structured plan, rendered as inline cards in the chat.
- **Two specialists, one conversation.** A lightweight Haiku router classifies each turn and dispatches it to the right specialist — a **meal/nutrition agent** (over the Spoonacular API) or an **exercise agent** (over ExerciseDB) — so the user never has to pick a mode.
- **Recipes on demand.** Ask "how do I make the salmon bowl?" and Franky resolves the dish from your saved plan and pulls full ingredients and steps.
- **Deterministic grocery lists.** The list itself is built by plain code, not an LLM — it sums and groups ingredients across a plan by canonical name and unit, with each item tagged by store section (produce, protein, etc.) for display. An LLM handles only the fuzzy parts the first time a plan's list is requested — normalizing ingredient names, reconciling units, assigning categories — and those results are cached so repeat requests are pure code.
- **Learns preferences.** 👍/👎 feedback on any meal or exercise updates a per-user preference summary that future plans respect. Users can view and correct what Franky "knows" about them.
- **Accounts & profiles.** Email/password auth with per-user profiles (height/weight/goals/restrictions); both partners' needs are always in context.

## Architecture

Two LLM specialists coordinated by a router, with deterministic code wherever a deterministic answer is possible:

```
                     ┌─────────────┐
   user message ───► │ coordinator │  (Haiku — routes each turn)
                     └──────┬──────┘
                ┌───────────┴───────────┐
          ┌─────▼─────┐           ┌─────▼──────┐
          │ meal agent │           │ exercise   │
          │ (Spoonacular)          │ agent      │
          └─────┬─────┘           │ (ExerciseDB)│
                │                  └─────┬──────┘
                └──────────┬─────────────┘
                  finalized plans (JSONB) ──► PostgreSQL
                           │
                  grocery list  ──►  pure code (grocery.py)
```

Every agent call is captured as a full **transcript** (system prompt, message history, tool calls, token usage, latency) for observability, and an **eval harness** (`evals/`) replays a seed task set through the coordinator and grades each run with code-based and LLM-as-judge graders (pass@k / pass^k).

The design decisions and slice-by-slice build history live in [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md); the full product vision is in [`docs/franky-fitness-prd.md`](docs/franky-fitness-prd.md).

## Tech stack

| Layer | Choice |
|---|---|
| AI | Anthropic Python SDK (Claude — Sonnet specialists, Haiku router) |
| Backend | FastAPI + Uvicorn (Python 3.13) |
| Frontend | React (Vite) + Tailwind CSS v4 |
| Database | PostgreSQL 17 (`psycopg2`) |
| Data modeling | Pydantic |
| External data | Spoonacular (recipes), ExerciseDB via RapidAPI (exercises) |

## Running it locally

**Prerequisites:** Python 3.13, Node 18+, PostgreSQL 17, and API keys for Anthropic, Spoonacular, and RapidAPI.

```bash
# 1. Clone and set up the Python environment
python3.13 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Create the database
createdb franky_fitness

# 3. Configure secrets — create a .env file in the repo root:
#    ANTHROPIC_API_KEY=...
#    SPOONACULAR_API_KEY=...
#    RAPIDAPI_KEY=...
#    DATABASE_URL=postgresql://localhost/franky_fitness

# 4. Start the backend (tables are created automatically on first boot)
uvicorn backend.main:app --reload          # http://localhost:8000

# 5. In a second terminal, start the frontend
cd frontend && npm install && npm run dev   # http://localhost:5173 (proxies /api → :8000)
```

Open http://localhost:5173, sign up, and start chatting.

## Tests & evals

```bash
# Fast, deterministic unit + DB-backed tests (no API calls)
python -m unittest discover tests

# Live eval harness — makes real Anthropic + Spoonacular/ExerciseDB calls, keep --trials small
python -m evals.harness --trials 3
```

## Project layout

```
backend/    FastAPI app — auth, coordinator, meal/exercise agents, grocery + preference logic
frontend/   Vite + React chat UI with inline plan/recipe/grocery cards
evals/      Eval harness (tasks, graders, pass@k/pass^k reporting)
tests/      stdlib unittest suite (grocery logic, saved items, profiles)
docs/        PRD, implementation plan, deployment guide, slice specs
models.py, spoonacular.py, exercisedb.py, grocery.py   shared models + API clients + pure grocery code
```

Deployment (Google Cloud Run + Cloud SQL) is documented in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).
