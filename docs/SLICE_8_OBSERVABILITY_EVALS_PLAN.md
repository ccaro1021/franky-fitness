# Slice 8 — Transcript Observability + Eval Harness (Implementation Plan)

> **Status:** Planned, not started. Drafted 2026-06-12. This is the execution
> spec for a fresh session. For *why*, see the Decision Log entry for 2026-06-12
> in [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md). Last shipped slice before
> this: Slice 7 (preference summary UI), committed/pushed as `f2c0583`.

## Goal

Two capabilities the user asked for:
1. **Easily access the prompt, output, tool calls, and which agent was invoked** for any chat turn.
2. **Run evals** following Anthropic's methodology in
   *["Demystifying Evals for AI Agents"](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)*.

The design is mapped as closely as possible to that article. The organizing
principle: **one `Transcript` abstraction, identical for live turns and eval
trials**, because the article's central workflow is *mining production traces
into eval cases*. Build in two phases — Phase 1 (capture) produces the exact
format Phase 2 (evals) consumes.

## Doc concept → Franky implementation (the alignment contract)

| Article concept | Definition (from the article) | Franky implementation |
|---|---|---|
| **Transcript** | "complete record of a trial — outputs, tool calls, reasoning, intermediate results… the full messages array at the end of a run," + token usage, latency, and the **outcome** (final environment state) | One `Transcript` record (`backend/transcripts.py`): `system`, `inputs` (messages), `steps` (each tool call w/ params + result), `output` (final text), `outcome` (structured plan + routing decision), `usage`, `latency_ms`, `model`, `agent_type`, `agent_invoked`. **Same schema** emitted by a live `/api/chat` turn and by an eval trial. |
| **Task** | "single test with defined inputs and success criteria"; *drawn from real failures* | `evals/tasks.py`: `{id, description, inputs, profile, success_criteria, graders, source}`. Seeded from **this project's own real failures** (the article's "bug tracker + support queue"). |
| **Trial** | "one attempt at a task; run multiple" | Harness runs **k trials/task** (default k=3), each with a **clean environment**: fresh synthetic profile, history reset, **no prod-DB writes**. |
| **Grader** | code-based (preferred) + model-based (when necessary); multiple graders/assertions per task; "grade what the agent produced, not the path it took" | `evals/graders.py`: code-based (routing/outcome/structure checks) + model-based LLM-as-judge for fuzzy cases. Graders read the `outcome`, never the tool path. |
| **Balanced dataset** | "test both when behaviors should and shouldn't occur" | Negative tasks paired with positive ones (see task list below). |
| **Evaluation harness** | "runs evals end-to-end, manages tools, records steps, aggregates" | `evals/harness.py`: runs tasks × trials via `run_coordinator()` directly, records each `Transcript` to `evals/results/<ts>/`, aggregates per-task + overall. |
| **Metrics** | pass@k (≥1 of k succeeds), pass^k (all k succeed) | Harness reports **both**; default k=3 → the PRD's **pass^3**. |
| **"Check the transcripts"** | read actual runs to validate graders | `python -m backend.view_transcript` (live) + harness writes readable per-trial transcripts (eval). |
| **Trace → task promotion** | build datasets from production traces | `promote_to_task(transcript)` helper turns a captured live `Transcript` into a `Task` scaffold. |
| **Framework choice** | "quickly pick a framework that fits… then invest energy in the evals themselves" | Minimal home-grown harness now; `Transcript` shaped to export to Braintrust/Langfuse/Phoenix later. Deliberately not over-investing in harness infra. |

## Storage decision (doc-aligned)

- **Canonical source of truth = JSONL `Transcript` records.** Live turns →
  gitignored `transcripts/` dir. Eval trials → `evals/results/<timestamp>/`.
  One format, so production traces feed the eval dataset by copy, not transform.
- **`agent_runs` is demoted to a queryable index** — keeps
  `agent_type`/`agent_invoked`/tokens/latency + a `transcript_id` pointer.
  **No prompt content in the DB** (keeps health data — weight/BMI/restrictions —
  out of Postgres; the privacy posture we kept returning to). Query pattern:
  `SELECT … WHERE agent_invoked='exercise'` → get `transcript_id` → open the JSONL.

---

## Phase 1 — Transcript capture

### 1a. `Transcript` schema + IO — `backend/transcripts.py` (NEW)
- A `Transcript` dataclass (or TypedDict) with the fields in the table above.
- `serialize_messages(messages) -> list[dict]`: convert Anthropic SDK content
  blocks (the `response.content` objects appended to `history` as
  `{"role":"assistant","content": response.content}`) into JSON-safe dicts.
  **This is the critical/tricky part** — `tool_use` blocks and `tool_result`
  blocks must round-trip losslessly.
- `extract_steps(messages) -> list[dict]`: pull `[{name, input, result}]` by
  pairing `tool_use` blocks with their matching `tool_result` (by `tool_use_id`).
- `new_transcript_id() -> str`: e.g. `secrets.token_hex(8)` or a UTC timestamp + short hash.
- `write_transcript(transcript, dir) -> path`: append one JSON object as a line
  to a JSONL file (live → `transcripts/<date>.jsonl`; eval → caller-specified dir).
- `read_transcripts(path|dir, filters)` + `promote_to_task(transcript) -> dict`
  (Task scaffold for Phase 2).

### 1b. Build the Transcript inside each agent
- `meal_agent.run_meal_agent` / `exercise_agent.run_exercise_agent`: they already
  hold `system`, the full `history` after the tool loop, and the final `message`.
  Add a `transcript` dict to the return value capturing system + serialized
  history (via `serialize_messages`) + extracted steps + output + outcome
  (`meal_plan`/`workout_plan`) + usage + latency + model. **No behavior change** —
  pure addition to the return dict.
- `coordinator._route`: return a small Transcript for the routing call
  (`system=ROUTER_SYSTEM_PROMPT`, `inputs=[last user msg]`, `output`=the chosen
  agent, the route `tool_use` as its single step, usage). 
- `coordinator.run_coordinator`: attach `agent_invoked` (the chosen specialist,
  e.g. `"exercise"`) to BOTH `agent_runs` entries, and carry each entry's
  `transcript` through so `main.py` can persist it.

### 1c. Schema — `backend/database.py`
- `agent_runs` gains, via `ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS …`
  (run inside `setup_tables()` so existing dev DBs upgrade in place on startup —
  `CREATE TABLE IF NOT EXISTS` will NOT add columns to the existing table):
  - `agent_invoked VARCHAR(20)`
  - `transcript_id VARCHAR(32)`
- Do **not** add prompt/messages columns — JSONL is canonical.

### 1d. Persist on each turn — `backend/main.py`
- In `chat()`, after `run_coordinator` returns: for each run in
  `result["agent_runs"]`, call `write_transcript(...)` and include
  `agent_invoked` + `transcript_id` in the existing `agent_runs` INSERT.

### 1e. Access CLI — `backend/view_transcript.py` (NEW)
```bash
python -m backend.view_transcript --last 1            # most recent turn, pretty-printed
python -m backend.view_transcript --agent exercise_agent --last 5
python -m backend.view_transcript --invoked exercise  # all turns routed to exercise
python -m backend.view_transcript --id <transcript_id>
```
Reads the JSONL (optionally cross-referencing `agent_runs` for filtering by
`agent_invoked`/`agent_type`/`user_id`), prints per run: agent_type,
agent_invoked, system prompt, each message, each tool call (name/input/result),
final output, tokens, latency.

### Phase 1 verification
- Send a meal chat turn and an exercise chat turn via the UI (localhost:5173).
- `python -m backend.view_transcript --last 2` shows both, with correct
  `agent_invoked`, full system prompt, tool calls, and output.
- `SELECT id, agent_type, agent_invoked, transcript_id FROM agent_runs ORDER BY id DESC LIMIT 4;`
  shows two rows/turn with a populated `transcript_id`.
- Confirm `transcripts/` is gitignored and no prompt content landed in Postgres.

---

## Phase 2 — Eval harness

### 2a. Transcript IO reuse — `evals/transcripts_io.py` (or import from `backend/transcripts.py`)
Reuse the Phase 1 `Transcript` schema verbatim. The harness produces the SAME
record shape for each trial.

### 2b. Tasks — `evals/tasks.py`
Each `Task`: `{id, description, inputs (messages list), profile (synthetic dict),
success_criteria (human-readable str), graders (list), source}`. Seed set (~6–8,
balanced positive/negative, mined from real project failures — grow toward the
article's 20–50 over time):

| id | inputs (gist) | success criteria | source |
|---|---|---|---|
| `meal_high_protein` | "Build me a high-protein weekly meal plan" | routed→meal; plan has 7 days; every meal ≥30g protein | core behavior |
| `meal_vegetarian_compliance` | profile has `vegetarian`; "plan my week" | no meat/fish ingredients in finalized plan | dietary-restriction risk |
| `exercise_dumbbell_only` | "3-day dumbbell-only program" | routed→exercise; 3 workout days; equipment ⊆ {dumbbell, body weight} | core behavior |
| `routing_recipe_howto` | "How do I make Monday's dinner?" (with saved plan) | routed→meal (NOT exercise) | routing correctness |
| `routing_workout_split` | "What's a good push/pull/legs split?" | routed→exercise | routing correctness |
| `clarify_before_plan` *(negative)* | "Help me eat better" (vague) | asks ONE clarifying question; does NOT emit a finalized plan | balanced/negative |
| `no_invented_macros` | "high protein breakfast ideas" | any macros cited trace to a `search_meals` step (not invented) | the "never invent macros" prompt rule |

> The `max_tokens=20` router bug and the `search_meals` API-failure handling from
> the decision log are also good task sources — add them as the dataset grows.

### 2c. Graders — `evals/graders.py`
- **Code-based** (deterministic; default): `routed_to(expected)`,
  `plan_has_n_days(n)`, `every_meal_min_protein(g)`, `no_restricted_ingredients(restrictions)`,
  `equipment_subset(allowed)`, `emitted_no_plan()` (for the clarify task),
  `macros_trace_to_search()`.
- **Model-based** (LLM-as-judge, only where necessary): `judge(rubric)` →
  Claude with a forced tool call returning `{passed: bool, reasoning: str}`.
  Used for `clarify_before_plan` ("did it ask exactly one focused clarifying
  question?") and any coaching-quality check.
- Each grader: `(transcript) -> {passed, assertion, reasoning}`. Graders read
  `transcript["outcome"]` and `transcript["agent_invoked"]` — **not the tool path**.

### 2d. Harness — `evals/harness.py`
- For each task × k trials: build a fresh synthetic profile, call
  `run_coordinator(task.inputs, profile, …)` directly (it's DB-free — no prod
  writes), build a `Transcript` from the result, run all the task's graders,
  record pass/fail per assertion.
- Aggregate **pass@k** and **pass^k** per task and overall. Print a summary table.
- Write every trial's `Transcript` to `evals/results/<timestamp>/<task_id>-trial<n>.jsonl`.
- CLI:
  ```bash
  python -m evals.harness --trials 3
  python -m evals.harness --trials 3 --task meal_high_protein
  ```

### 2e. `evals/README.md`
How to run; how to add a task from a real failure (the "could a human SME
independently agree on pass/fail?" check from the article); note this is the
living regression set (article step 8: long-term ownership).

### Phase 2 verification
- `python -m evals.harness --trials 3` runs all tasks, prints pass@3 + pass^3 per
  task and overall, writes transcripts under `evals/results/`.
- Deliberately break a prompt rule (e.g. drop the 30g-protein line) and confirm
  `meal_high_protein` drops to a failing pass^3 — proves the graders bite.

---

## Files summary
**Phase 1:** `backend/transcripts.py` (NEW), `backend/view_transcript.py` (NEW),
`backend/database.py` (+2 columns), `backend/meal_agent.py`,
`backend/exercise_agent.py`, `backend/coordinator.py`, `backend/main.py`.
**Phase 2:** `evals/__init__.py`, `evals/tasks.py`, `evals/graders.py`,
`evals/harness.py`, `evals/transcripts_io.py` (or reuse backend), `evals/README.md`.
**Hygiene/docs:** `.gitignore` += `transcripts/` and `evals/results/`;
`CLAUDE.md` + `IMPLEMENTATION_PLAN.md` mark Slice 8 done when complete.

## Cost note
Both `view_transcript` (free, reads local data) and the harness differ: the
**harness makes real Anthropic + Spoonacular/ExerciseDB calls** per trial, so keep
the seed task set small and `--trials` configurable.

## Suggested build order
1. Phase 1a (`Transcript` schema + `serialize_messages` — get the serialization
   of tool_use/tool_result blocks right first; everything depends on it).
2. Phase 1b–1e (wire capture through agents → main → CLI), verify.
3. Phase 2b–2c (tasks + graders), then 2d harness, verify with a deliberately
   broken prompt rule.
4. Docs + commit. Likely two commits (one per phase).
