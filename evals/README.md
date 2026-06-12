# Franky Fitness — Eval Harness

Mapped to Anthropic's
["Demystifying Evals for AI Agents"](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents).
See `docs/SLICE_8_OBSERVABILITY_EVALS_PLAN.md` for the full design.

## Running

```bash
source venv/bin/activate
python -m evals.harness --trials 3                       # full suite, k=3
python -m evals.harness --trials 3 --task meal_high_protein   # single task
```

Each trial calls `run_coordinator()` directly — no Postgres writes, no UI
needed. **This makes real Anthropic + Spoonacular/ExerciseDB API calls**, so
keep `--trials` small while iterating.

The harness prints a `pass@k` / `pass^k` table per task and overall, and
writes every trial's Transcript to `evals/results/<timestamp>/<task_id>-trial<n>.jsonl`
(gitignored). These are the *same* Transcript format as live `transcripts/`
records — view them with:

```bash
python -m backend.view_transcript --dir evals/results/<timestamp>
```

## How it works

- **Task** (`evals/tasks.py`): `{id, description, inputs, profile, current_meal_plan,
  current_workout_plan, success_criteria, graders, source}`.
- **Trial**: one run of a task through `run_coordinator()` with a fresh copy of
  its inputs/profile. `k` trials per task (default 3).
- **Grader** (`evals/graders.py`): `(transcript) -> {assertion, passed, reasoning}`.
  Graders read only `transcript["outcome"]` and `transcript["agent_invoked"]` —
  never the tool-call path — so they stay valid if an agent's internal tool-use
  sequence changes. Code-based graders are preferred; `judge(rubric)` is an
  LLM-as-judge for fuzzy checks (e.g. "asked exactly one clarifying question").
- **pass@k**: at least one of the k trials passed all its graders.
- **pass^k**: all k trials passed all their graders.

## Adding a task from a real failure

1. Find the failing turn: `python -m backend.view_transcript --last 5` (or
   filter with `--agent`/`--invoked`).
2. Write down, in plain language, what *should* have happened — then ask:
   could a human SME independently look at the transcript and agree on
   pass/fail using that description? If not, refine it before writing a
   grader.
3. Add a new entry to `TASKS` in `evals/tasks.py`: copy the failing user
   message(s) into `inputs`, build a synthetic `profile` (and
   `current_meal_plan`/`current_workout_plan` if the failure depended on
   saved-plan context), and write `graders` that check the `outcome` against
   your success criteria. `backend.transcripts.promote_to_task()` can
   bootstrap the scaffold from a captured Transcript.
4. Run `python -m evals.harness --trials 3 --task <new_id>` to confirm it
   fails the way you expect *before* fixing the underlying issue, then again
   after the fix to confirm it now passes.

## Long-term ownership

This is a living regression set. Keep the balance of positive/negative tasks
as it grows — pair "should happen" tasks (e.g. `meal_high_protein`) with
"shouldn't happen" tasks (e.g. `clarify_before_plan`). Grow toward ~20-50
tasks over time, per the article's guidance, prioritizing tasks mined from
real production transcripts over hypothetical cases.
