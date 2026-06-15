# Slice 13 — Profile Onboarding + Chat-Driven Profile Updates (PRD)

> **Status:** Drafted 2026-06-15 via a `/grill-me` session, not yet built.
> Last shipped slice before this: Slice 12 (grocery category set update).

## Problem Statement

Franky's meal and exercise recommendations are only as good as the profile
data behind them (dietary restrictions, fitness goals, height/weight, notes).
Today, a brand-new user signs up, lands directly in Chat with an empty
profile, and has no prompt to fill anything in — Franky can build a "generic"
plan immediately, but it won't be tailored. Separately, even users who do fill
out some profile fields have no way to update them except by navigating to the
Profile page and editing form fields directly — if they mention new
information conversationally ("I'm vegetarian now," "I'm down to 165 lbs"),
Franky has no way to remember it for next time.

## Solution

1. When a new user signs up, they're guided to the Profile page with a banner
   explaining that filling in stats/goals/restrictions helps Franky build
   better meal and workout plans — and Franky's first chat message reinforces
   this with an invitation to share that info conversationally instead, if
   they'd rather.
2. Franky (both the meal and exercise specialists) gets a new `update_profile`
   tool. When a user states durable personal info in chat (height, weight,
   target weight, dietary restrictions, fitness goals, general notes), Franky
   saves it to their profile immediately and confirms what it saved in its
   reply — no separate confirmation round-trip.
3. When Franky is about to finalize a meal or workout plan and key profile
   fields are still empty, it mentions — once, as part of its normal reply —
   that providing that info (via chat or the Profile page) would let it
   tailor the plan better.

## User Stories

1. As a new user, when I sign up, I want to land on my Profile page with an
   explanation of why this information matters, so that I understand the
   value of filling it in before I start chatting.
2. As a new user, I want to be able to dismiss the onboarding banner and go
   straight to Chat if I'd rather provide info conversationally or skip it for
   now, so that the onboarding doesn't feel like a blocker.
3. As a new user who dismisses the banner and goes to Chat, I want Franky's
   first message to mention that sharing my stats/goals/restrictions (in chat
   or via Profile) will help it build better plans, so that I still get the
   prompt even if I skip the Profile page.
4. As a returning user with an empty profile, I want logging in to behave
   normally (land on Chat, no forced redirect), so that the onboarding nudge
   doesn't become an annoying recurring interruption.
5. As a user, when I tell Franky my height and weight in chat (e.g. "I'm 5'10
   and 190 lbs"), I want it to save those to my profile automatically, so that
   future plans use accurate BMI/calorie context without me re-entering it on
   the Profile page.
6. As a user, when I tell Franky my target weight (e.g. "I want to get down to
   175 lbs"), I want that saved to my profile, so that future meal plans can
   be paced toward that goal.
7. As a user, when I tell Franky about a new dietary restriction (e.g. "I just
   found out I'm allergic to shellfish"), I want it added to my existing
   dietary restrictions without losing the ones I already had, so that my
   profile accumulates accurate information over time.
8. As a user, when I tell Franky about a new fitness goal (e.g. "I want to
   start training for a 10k"), I want it added to my existing fitness goals
   without replacing the ones I already had, so my goals build up rather than
   overwrite each other.
9. As a user, when I mention something Franky should remember generally (e.g.
   "I have a bad knee, go easy on lunges"), I want that appended to my profile
   notes, so it's preserved verbatim and visible on my Profile page.
10. As a user, after Franky updates my profile from chat, I want its reply to
    tell me exactly what it saved (e.g. "Got it — updated your weight to 165
    lbs and added 'vegetarian' to your dietary restrictions"), so I can
    correct it immediately if it misunderstood.
11. As a user, after Franky updates my profile from chat, I want to see those
    changes reflected when I visit the Profile page, so chat and the Profile
    page never disagree about my current info.
12. As a user asking for a meal plan with no fitness goals and no
    height/weight set, I want Franky to mention — once, as part of its normal
    reply alongside the plan — that providing that info would let it tailor
    the plan better, so I know how to get more personalized results next time.
13. As a user asking for a workout plan with no fitness goals set, I want
    Franky to mention that providing fitness goals would help it tailor the
    program, so I understand what's missing.
14. As a user who has already provided fitness goals and height/weight, I
    don't want Franky to repeat the "fill out your profile" reminder on every
    plan request, so the experience doesn't feel nagging once I've provided
    the key info.
15. As a user, if I mention a one-off preference that isn't meant to persist
    (e.g. "actually, swap Tuesday's dinner for something else"), I don't want
    Franky to misinterpret that as a profile update, so my stored profile only
    reflects durable info.
16. As a developer, I want `update_profile`'s list-merging and note-appending
    logic covered by DB-backed unit tests (mirroring `tests/test_saved_items.py`),
    so the merge/dedupe/append semantics are verified independent of any LLM
    call.
17. As a developer, I want an eval task that checks the agent calls
    `update_profile` with correct arguments when the user states profile info
    in conversation, so regressions in tool-use are caught by
    `python -m evals.harness`.
18. As a developer, I want an eval task that checks Franky's reply mentions
    profile completeness when a synthetic user with an empty profile requests
    a plan, so regressions in the reminder behavior are caught by the eval
    harness.
19. As a developer running the eval harness (which is DB-free by design), I
    want `update_profile` tool calls to execute without a real `user_id` or
    Postgres row, so existing eval tasks continue to run without new DB
    dependencies.

## Implementation Decisions

### Onboarding (frontend-only, signup-flow flag, not persisted)
- `AuthPage`'s signup path passes an `isNewSignup: true` flag up through
  `onAuth` (alongside the user object) — login does not set this flag.
- `App.jsx` uses `isNewSignup` to set its initial `view` state to `'profile'`
  instead of `'chat'`, and passes a `showOnboardingBanner` prop (derived from
  the same flag) to `ProfilePage`.
- `ProfilePage` renders a dismissible banner above the Stats card when
  `showOnboardingBanner` is true, explaining that this info helps Franky build
  better meal/workout plans. Dismissing it clears local state only — no new DB
  column, no "onboarding_seen" persistence. A user who dismisses and later
  logs back in with an empty profile sees the normal Chat-first experience
  (no redirect).
- `Chat.jsx`'s hardcoded initial greeting (currently a static string built in
  `useState`) gets an additional sentence when `isNewSignup` is true, inviting
  the user to share stats/goals/restrictions in chat or via the Profile page.
  This is a pure frontend string change — no new agent call for the greeting.

### `update_profile` tool (shared schema/handler, added to both agents)
- Added to both `meal_agent.TOOLS` and `exercise_agent.TOOLS` with an
  identical input schema:
  - `height_inches` (number, optional) — overwrites if provided.
  - `weight_lbs` (number, optional) — overwrites if provided.
  - `target_weight_lbs` (number, optional) — overwrites if provided.
  - `add_dietary_restrictions` (array of strings, optional) — merged into the
    existing list, case-insensitive de-duped.
  - `add_fitness_goals` (array of strings, optional) — merged into the
    existing list, case-insensitive de-duped.
  - `append_notes` (string, optional) — appended to the existing `notes` value
    on a new line; existing notes are preserved verbatim.
  - No `remove_*` inputs in this slice — removal stays a Profile-page-only
    action (existing comma-separated text fields).
- New `backend.users.patch_profile(user_id, **fields)`: reads the current
  profile, applies only the provided fields (partial update — fields not
  present in the call are left untouched), performs the merge/dedupe/append
  logic for list and notes fields, persists via the existing `profiles` table
  update path, and returns the refreshed profile (same shape as
  `get_profile`/`update_profile`'s return value, including computed `bmi`).
- `_run_tool` in both `meal_agent.py` and `exercise_agent.py` gains an
  `user_id: int | None` parameter. `run_meal_agent`/`run_exercise_agent`/
  `run_coordinator` thread this through from `/api/chat` (which has
  `user["id"]` available via `get_current_user`).
  - When `user_id` is set: `_run_tool("update_profile", inputs, user_id)`
    calls `patch_profile` and builds its tool_result text from the *returned,
    merged* profile (e.g. full updated dietary restrictions list), so Franky's
    confirmation reflects the true persisted state.
  - When `user_id` is `None` (eval harness): skips the DB write entirely, but
    still returns a descriptive tool_result text based purely on the tool
    call's inputs (e.g. "Noted: weight 165 lbs, added dietary restriction
    'vegetarian'") so the conversation continues naturally and the transcript
    still records the `tool_use` input/`tool_result` step pair for grading.
- System prompt additions (both agents' `_build_system_prompt`):
  - Instructs Franky to call `update_profile` when the user states durable
    personal info meant to persist (stats, goals, restrictions, general notes
    like injuries) — not for one-off, single-request preferences (e.g.
    "swap Tuesday's dinner").
  - Instructs Franky to confirm in its reply what was saved, in plain
    language, without restating the entire profile.

### Pre-finalize reminder (prompt-driven, no new tool)
- Meal agent (`_build_system_prompt` in `meal_agent.py`): if `fitness_goals`
  is empty, OR both `height_inches` and `weight_lbs` are empty/unset, the
  prompt instructs Franky to include one short sentence in its reply alongside
  `finalize_meal_plan` noting that providing that info (via chat or Profile)
  would let it tailor the plan further. If those fields are already populated,
  no reminder is added.
- Exercise agent (`_build_system_prompt` in `exercise_agent.py`): same
  mechanism, triggered only by empty `fitness_goals`. Equipment/injury
  questions remain handled conversationally per-session as today (unchanged).
- This is computed once per system-prompt build from the `profile` dict
  already passed into `_build_system_prompt` — no additional DB reads.

## Testing Decisions

- **`tests/test_users.py` (new, DB-backed, mirrors `tests/test_saved_items.py`'s
  pattern of using a real local Postgres connection via `unittest`)**:
  - `patch_profile` overwrites scalar fields (`height_inches`, `weight_lbs`,
    `target_weight_lbs`) when provided, and leaves them untouched when omitted
    (partial update).
  - `patch_profile` merges `add_dietary_restrictions`/`add_fitness_goals` into
    existing lists with case-insensitive de-duplication (e.g. adding
    "Vegetarian" when "vegetarian" already exists doesn't create a duplicate).
  - `patch_profile` appends `append_notes` to existing `notes` on a new line,
    preserving prior content; appending to empty `notes` doesn't leave a
    leading blank line.
  - Returned profile shape matches `get_profile`'s (including computed `bmi`).
  - These are pure DB + Python tests — no LLM/API calls, consistent with
    `tests/test_grocery.py`'s "no API calls" rule for the `tests/` package.

- **`evals/tasks.py` — two new tasks**, graded via `evals/graders.py` and run
  through `python -m evals.harness --trials N --task <id>`:
  - A task where the synthetic conversation has the user state new profile
    info (e.g. height/weight + a dietary restriction) while asking for a meal
    plan. Code-based grader reads `transcript["steps"]` for a `tool_use` named
    `update_profile` with the expected fields present in its input — testing
    *that the tool was called correctly*, not the DB write (per Implementation
    Decisions, `user_id` is `None` in harness runs, so no DB write occurs).
  - A task with a synthetic profile that has empty `fitness_goals` and empty
    `height_inches`/`weight_lbs`, requesting a meal plan. LLM-as-judge grader
    (`judge(rubric)`) checks that the final reply mentions that providing
    profile info would help tailor the plan — testing *the reminder behavior*
    via `transcript["outcome"]`/final output text.
  - Both follow the existing seed-task shape in `evals/tasks.py`
    (`{id, description, inputs, profile, current_meal_plan, current_workout_plan,
    success_criteria, graders, source}`).

- **No new tests for the onboarding banner/greeting** — these are static
  frontend string/prop changes with no business logic; covered by manual
  verification via the `run` skill (signup flow → Profile redirect + banner →
  Chat greeting).

## Out of Scope

- Removing items from `dietary_restrictions`/`fitness_goals` via chat
  (`remove_*` tool inputs) — stays a Profile-page-only edit for this slice.
- Persisting "has the user seen onboarding" server-side (`onboarding_seen`
  column or similar) — onboarding is signup-flow-only and in-memory.
- A dedicated frontend component/card visualizing profile updates from chat —
  Franky's text confirmation is sufficient; the Profile page already re-fetches
  on mount and will show the new values whenever the user navigates there.
- Re-prompting users with incomplete profiles on every login or every chat
  turn — the reminder is scoped to the moment a plan is finalized, and only
  when the specific key fields (per agent) are empty.
- Changing how `current_plan`/preference-summary context is built — the
  pre-finalize reminder is computed from the existing `profile` dict already
  passed into `_build_system_prompt`, no new context plumbing.
- Validating or sanity-checking the *values* Franky writes (e.g. implausible
  height/weight) — trusts the model's extraction, same trust level as existing
  `finalize_meal_plan`/`finalize_workout_plan` inputs.

## Further Notes

- This slice touches both specialist agents identically for `update_profile`
  — keep the tool schema, `_run_tool` branch, and system-prompt wording in
  sync between `meal_agent.py` and `exercise_agent.py` to avoid drift (no
  shared module currently exists for agent tool definitions; if a third
  agent-shared tool emerges in a future slice, consider extracting a common
  `backend/agent_tools.py`).
- `build_profile_context(user_id)` (in `backend/users.py`) is called once per
  `/api/chat` request, before the agent runs. If `update_profile` fires mid-turn,
  the system prompt for that turn was built from pre-update data — this is
  fine, since the tool_result text (built from the post-update profile) is
  what Franky uses to confirm, and the next `/api/chat` call rebuilds the
  system prompt fresh from the DB.
- The CLAUDE.md slice-log entries for Slices 1–12 follow a consistent
  "**Slice N (done): Title.** ..." format in both `CLAUDE.md` and
  `docs/IMPLEMENTATION_PLAN.md`'s build-order checklist + decision log — once
  this slice is built, add corresponding entries following that same format.
