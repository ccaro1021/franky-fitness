# Slice 9 — Grocery Normalization Agent (Implementation Plan)

> **Status:** Built. Drafted 2026-06-15 via a `/grill-me` session on
> `grocery.py`'s alias table, implemented 2026-06-15. For *why*, see the
> Decision Log entry for 2026-06-15 in [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md),
> which also revises **Decision 3**. Last shipped slice before this: Slice 8
> (transcript observability + eval harness), committed/pushed through `c8f609f`.

## Goal

Replace the hand-maintained `_INGREDIENT_ALIASES` dict in `grocery.py` — which
cannot keep up with the long tail of Spoonacular ingredient phrasing — with an
LLM-backed normalization step that maps each raw recipe ingredient string to
its **purchasable base item** (e.g. "2 cups shredded cheddar, divided" →
"shredded cheddar"; "1 clove garlic, minced" → "minced garlic"). Summing,
rounding, and store-section categorization remain pure code, unchanged from
today — **this is a hybrid, not a full grocery agent**, and it revises rather
than reverses Decision 3.

## Why an LLM for this and not the rest

Normalization is a judgment call — "would a shopper buy a different item off
the shelf for this?" — that a static dict can only ever cover for strings
someone has already seen and hand-encoded (the 2026-06-15 alias audit took
three commits to get ~89 entries right, and Spoonacular will keep returning
phrasing variants forever). Summing quantities and bucketing by store section
remain arithmetic/keyword-matching with no judgment involved — Decision 3's
original rationale for *that* part still holds and that code doesn't change.

## The contract

**Input:** the final, saved `plan.meals` list (after any future meal
removal/replacement — see "Out of scope" below) — each meal has
`name`/`calories`/`protein_g`/`carbs_g`/`fat_g`/`spoonacular_id`.

**Output:** the same `list[GroceryItem]` shape `generate_grocery_list` returns
today (`name`, `total_quantity`, `unit`, `category`) — **no API/frontend
contract change**. `GroceryListCard.jsx` and `/api/plans/{id}/grocery-list`
are unaffected.

## Flow

1. User clicks "Grocery List" (`MealPlanCard`) or types "grocery list" in chat
   (`/api/chat`'s existing short-circuit, `backend/main.py:196-204`).
2. If `plan.content["grocery"]` is already fully populated (Q5/Q10 — persisted
   from a prior generation, no meals pending retry), skip straight to step 6.
3. For each meal in `plan.meals` **without** stored ingredients (new meals, or
   meals whose `get_recipe` failed last time — Q11c), call
   `spoonacular.get_recipe(spoonacular_id)`. Failures are logged and that
   meal's ingredients stay pending for next time; success stores
   `meal["ingredients"]` in `plan.content`.
4. Collect the full set of raw ingredient name strings across all meals.
   Look each up in the `ingredient_normalizations` cache table (Q7).
   Cache misses go to the normalizer LLM call in **one batch** (Q3) —
   `claude-opus-*` (Q15), forced tool call returning
   `[{raw_name, canonical_name}, ...]`. Results are upserted into the cache.
5. Persist the per-ingredient canonical names back onto `plan.content`
   alongside the fetched ingredients (Q5/Q10).
6. `grocery.generate_grocery_list(plan)` — **unchanged logic** — sums
   quantities by canonical name and calls `categorize_ingredient` (unchanged
   `_CATEGORY_KEYWORDS`), using the canonical names now stored on each
   ingredient instead of a static dict lookup.

Steps 3-5 are skipped entirely once a plan's grocery data is fully cached
(every meal has ingredients, every raw ingredient has a cache hit) — which is
the steady state after the first generation.

## Out of scope (separate slice)

**Meal removal + auto-replacement to hit calorie/macro targets** is its own
feature with its own design surface (where removal happens in the UI, who
finds the replacement, whether macros rebalance per-slot or per-week). This
slice's contract is simply "operate on whatever `plan.meals` is at save/grocery
time" — robust to that feature landing later without changes here.

## Schema changes

### New table: `ingredient_normalizations` (global cache, Q6/Q7)
```sql
CREATE TABLE IF NOT EXISTS ingredient_normalizations (
    raw_name VARCHAR(255) PRIMARY KEY,
    canonical_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
)
```
- `raw_name` is the lowercased ingredient string as it comes from Spoonacular.
- Seeded at migration time from `_INGREDIENT_ALIASES` (Q9): for each
  `(key, value)` in the existing dict, insert `(key, value)`; for every base
  item we deliberately did *not* alias (the audit's "keep as written" entries
  — e.g. "minced garlic", "dried basil", "red bell pepper"), insert
  `(item, item)` as a self-mapping so they're cache hits too, not LLM calls.
- Corrections to a bad LLM-generated entry: manual `UPDATE`/`DELETE` via
  `psql`, same as the project's existing debugging style (CLAUDE.md
  "Debugging" section) — no correction UI (Q9).

### `plans.content` (existing JSONB column, no migration)
Each meal gains an `ingredients` field (raw Spoonacular ingredients, as today)
plus a parallel `canonical_names` mapping (or each ingredient gets an inline
`canonical_name` key) once normalized. A plan-level flag or per-meal
`ingredients_fetched: bool` tracks which meals still need `get_recipe` /
normalization on the next request (Q11c retry).

## Module boundaries (Q14)

- **`grocery.py`** (existing, mostly unchanged): keeps `_CATEGORY_KEYWORDS`,
  `categorize_ingredient`, `generate_grocery_list`. `_INGREDIENT_ALIASES` is
  **removed** (its content moves to the DB seed + prompt guidance below).
  `generate_grocery_list` reads `canonical_name` off each ingredient instead
  of looking it up in a dict.
- **`backend/grocery_agent.py`** (NEW, mirrors `meal_agent.py`/
  `exercise_agent.py`'s module shape but is a single batch call, not a
  tool-use loop — closer to `coordinator._route`): owns the
  `ingredient_normalizations` cache (lookup + upsert), the few-shot prompt,
  and the `normalize_ingredients(raw_names: list[str]) -> dict[str, str]` LLM
  call. Returns a `Transcript` (Q12, `agent_type="grocery_normalizer"`) when
  it actually calls the LLM (i.e., on cache misses).
- **`tests/test_grocery.py`**: rewritten to stub the cache lookup (a plain
  dict) instead of `_INGREDIENT_ALIASES` — the summing/categorization/
  integrity tests (17 tests, 2026-06-15) stay conceptually the same, just
  fed canonical names from a stub instead of the removed dict.
- **`evals/`**: new task(s) for normalization *quality* — e.g. feed a novel
  ingredient string that should follow an audited pattern (a new dried herb,
  a new bell-pepper color) and grade whether `grocery_agent.normalize_ingredients`
  preserves the pattern. This is LLM-judgment territory (real API calls,
  small trial counts), not `tests/`.

## Few-shot guidance prompt (Q10)

A curated ~15-20 example subset of the audit's *patterns* (not the full
89-entry table — mechanical cases are cache hits and don't need LLM
reasoning), one or two per pattern:

- Fresh vs. dried herbs stay separate ("fresh basil" → "basil", "dried basil"
  → "dried basil")
- Color/cut variants are separate purchases ("red bell pepper" stays "red bell
  pepper"; "boneless skinless chicken breast" stays as-is)
- Salted vs. unsalted butter stay separate
- "Prepared form ≠ raw form" — almond flour ≠ almonds, breadcrumbs ≠ bread,
  tomato paste ≠ tomatoes, coconut milk ≠ coconut, vanilla extract ≠ vanilla
  beans, chicken broth ≠ chicken
- Mechanical normalization still applies for novel strings that fit existing
  mechanical patterns (plurals, "fresh"/extra descriptors that don't change
  the product) — e.g. egg components → eggs

## Error handling (Q11)

- `get_recipe` failure for a meal → that meal's `ingredients_fetched` stays
  `false`; grocery list is generated from the meals that succeeded; response
  notes which meal(s) are missing. Next "Grocery List" click retries only the
  missing meal(s) — never written to the persisted cache as a permanent empty
  result.
- Normalizer LLM call always returns a canonical name for every input (Q13,
  no "uncertain" bucket) — worst case is an odd-looking but harmless line item,
  observable via the Q12 transcript if it becomes a recurring pattern.

## Model choice (Q15)

`claude-opus-*` (latest available at implementation time) for
`grocery_agent.normalize_ingredients`. Justified specifically by the caching
architecture: this call runs on **cache misses only** — rare after the first
few weeks of real usage — so optimizing for correctness on novel/edge-case
ingredients matters more than the cost difference, and a wrong Haiku-quality
call would be **cached and silently wrong forever** until manually fixed via
`psql`.

## Files summary

**New:** `backend/grocery_agent.py`, migration for `ingredient_normalizations`
(+ seed data derived from current `_INGREDIENT_ALIASES`) in
`backend/database.py`'s `setup_tables()`.
**Modified:** `grocery.py` (remove `_INGREDIENT_ALIASES`, read `canonical_name`
from ingredients), `backend/meal_agent.py` (`finalize_meal_plan` stops calling
`get_recipe` — stores name/macros/`spoonacular_id` only), `backend/main.py`
(grocery-list paths call the new flow), `tests/test_grocery.py` (stub cache).
**Eval:** new normalization-pattern task(s) in `evals/`.

## Suggested build order

1. `ingredient_normalizations` table + seed migration from
   `_INGREDIENT_ALIASES` (verify seed rows via `psql` before anything else
   depends on them).
2. `backend/grocery_agent.py`: cache lookup/upsert + few-shot prompt +
   `normalize_ingredients`, with its `Transcript`. Unit-testable independent
   of the rest (mock the cache, mock the LLM call).
3. `grocery.py`: remove `_INGREDIENT_ALIASES`, switch `generate_grocery_list`
   to read `canonical_name`. Update `tests/test_grocery.py` to stub the cache.
4. `backend/meal_agent.py`: defer `get_recipe` out of `finalize_meal_plan`.
5. Wire the full flow into `backend/main.py`'s grocery-list paths (button +
   chat short-circuit), including persistence and per-meal retry tracking on
   `plans.content`.
6. Verify end-to-end: new plan → first "Grocery List" click (cache misses,
   normalizer transcript written) → second click (zero LLM/Spoonacular calls,
   confirm via logs/transcripts) → remove a meal manually in `psql` and
   re-click (only the remaining meals' ingredients used).
7. Eval task(s) for normalization-pattern generalization; docs + commit.
