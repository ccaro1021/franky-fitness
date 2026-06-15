"""Eval: does grocery_agent.normalize_ingredients generalize the 2026-06-15 alias-audit
patterns (fresh/dried, color variants, cut descriptors, prepared-form != raw-form) to
*novel* ingredient strings it hasn't seen before? Also checks
grocery_agent.reconcile_quantities' unit-conversion and categorization judgment.

    python -m evals.grocery_normalization
    python -m evals.grocery_normalization --task novel_dried_herb
    python -m evals.grocery_normalization --task cross_unit_olive_oil

Each TASKS entry clears any cached entry for its raw ingredient string (forcing a
real LLM call via grocery_agent.normalize_ingredients), then grades the resulting
canonical name with an LLM judge against the pattern it should follow. Each
RECONCILE_TASKS entry calls grocery_agent.reconcile_quantities (uncached) and
grades the resulting unit/multiplier/category mapping. This is LLM-judgment
territory (real Anthropic calls) — keep the task lists small, like evals/harness.py.
"""

import argparse

from backend.database import get_connection
from backend.grocery_agent import normalize_ingredients, reconcile_quantities
from evals.graders import judge

TASKS = [
    {
        "id": "novel_dried_herb",
        "raw_name": "dried tarragon",
        "rubric": (
            "The canonical name for 'dried tarragon' keeps the 'dried' descriptor "
            "(e.g. 'dried tarragon'), not collapsed to 'tarragon' — dried herbs are "
            "a separate spice-aisle purchase from fresh herbs."
        ),
    },
    {
        "id": "novel_bell_pepper_color",
        "raw_name": "orange bell peppers",
        "rubric": (
            "The canonical name for 'orange bell peppers' keeps the color and is "
            "singular (e.g. 'orange bell pepper'), not collapsed to a generic "
            "'bell pepper' — pepper color is a distinct purchase."
        ),
    },
    {
        "id": "novel_prepared_form",
        "raw_name": "almond butter",
        "rubric": (
            "The canonical name for 'almond butter' is 'almond butter' or very "
            "close to it, NOT 'almonds' — a prepared/processed form is a "
            "different product from the raw ingredient."
        ),
    },
    {
        "id": "novel_mechanical_plural",
        "raw_name": "vine-ripened tomatoes",
        "rubric": (
            "The canonical name for 'vine-ripened tomatoes' is 'tomato' (singular, "
            "base produce item) — this is a mechanical plural/descriptor case, not "
            "a distinct-purchase case."
        ),
    },
]


# reconcile_quantities is uncached (no global table), so these tasks always make
# a real LLM call — keep this list small, like TASKS above.
RECONCILE_TASKS = [
    {
        "id": "cross_unit_olive_oil",
        "items": [
            {"canonical_name": "olive oil", "unit": "tbsp"},
            {"canonical_name": "olive oil", "unit": "cup"},
        ],
        "rubric": (
            "Both 'tbsp' and 'cup' entries for 'olive oil' resolve to the SAME "
            "target_unit. The multiplier converting 'tbsp' to that target_unit is "
            "approximately 1/16 (0.0625) if the target is 'cup', or 1.0 if the "
            "target is 'tbsp' (with the 'cup' entry's multiplier approximately 16 "
            "in that case) — either way the two multipliers should be consistent "
            "with 1 cup = 16 tbsp. The category for 'olive oil' is 'pantry'."
        ),
    },
]


def _clear_cache(raw_name: str) -> None:
    """Delete any cached entry for raw_name so the next normalize_ingredients call hits the LLM."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ingredient_normalizations WHERE raw_name = %s", (raw_name.lower(),))
        conn.commit()


def run_task(task: dict) -> dict:
    """Run one normalization task. Returns {task_id, raw_name, canonical_name, assertion, passed, reasoning}."""
    _clear_cache(task["raw_name"])
    mapping, _transcript = normalize_ingredients([task["raw_name"]])
    canonical_name = mapping[task["raw_name"].lower()]

    result = judge(task["rubric"])({"output": canonical_name})
    return {"task_id": task["id"], "raw_name": task["raw_name"], "canonical_name": canonical_name, **result}


def run_reconcile_task(task: dict) -> dict:
    """Run one unit-reconciliation task. Returns {task_id, mapping, assertion, passed, reasoning}."""
    mapping, _transcript = reconcile_quantities(task["items"])

    output = "\n".join(
        f"{name} ({unit}) -> target_unit={reconciled['target_unit']}, "
        f"multiplier={reconciled['multiplier']}, category={reconciled['category']}"
        for (name, unit), reconciled in mapping.items()
    )

    result = judge(task["rubric"])({"output": output})
    return {"task_id": task["id"], "mapping": mapping, **result}


def main():
    parser = argparse.ArgumentParser(description="Run the grocery normalization pattern-generalization eval")
    parser.add_argument("--task", help="Run only this task id")
    args = parser.parse_args()

    tasks = [t for t in TASKS if t["id"] == args.task] if args.task else TASKS
    reconcile_tasks = [t for t in RECONCILE_TASKS if t["id"] == args.task] if args.task else RECONCILE_TASKS

    passed_count = 0
    total_count = len(tasks) + len(reconcile_tasks)
    for task in tasks:
        result = run_task(task)
        mark = "PASS" if result["passed"] else "FAIL"
        passed_count += result["passed"]
        print(f"[{mark}] {result['task_id']}: '{result['raw_name']}' -> '{result['canonical_name']}'")
        print(f"       {result['reasoning']}")

    for task in reconcile_tasks:
        result = run_reconcile_task(task)
        mark = "PASS" if result["passed"] else "FAIL"
        passed_count += result["passed"]
        print(f"[{mark}] {result['task_id']}: {result['mapping']}")
        print(f"       {result['reasoning']}")

    print(f"\n{passed_count}/{total_count} passed")


if __name__ == "__main__":
    main()
