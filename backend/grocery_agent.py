"""Ingredient normalization: map raw Spoonacular ingredient strings to purchasable
canonical names, backed by a global ingredient_normalizations cache table.

This is a single batch call, not a tool-use loop (see meal_agent.py/exercise_agent.py
for that shape) — closer to coordinator._route. It only calls the LLM on cache
misses, which should be rare once the cache fills.
"""

import time

from anthropic import Anthropic
from dotenv import load_dotenv

from backend.database import get_connection
from backend.transcripts import build_transcript

load_dotenv()

client = Anthropic()

# Cache misses are rare but cached forever — pay for correctness over cost here.
MODEL = "claude-opus-4-1-20250805"

SYSTEM_PROMPT = """You normalize raw recipe ingredient strings into purchasable \
grocery items — the name a shopper would look for on a shelf or in a store app.

Apply these patterns, drawn from a prior audit of this project's grocery list:

- Depluralize and drop redundant descriptors for common produce and pantry \
staples: "tomatoes" -> "tomato", "extra virgin olive oil" -> "olive oil", \
"garlic cloves" -> "garlic".
- Egg components collapse to the whole item: "egg yolks", "egg whites", \
"large eggs" -> "eggs".
- Milk fat-content variants collapse to one purchase: "whole milk", "2% milk", \
"2% reduced fat milk", "skim milk", "low-fat milk" -> "milk".
- Fresh vs. dried herbs are DIFFERENT purchases — keep "dried" in the name: \
"fresh basil" -> "basil", "dried basil" -> "dried basil".
- Color and cut variants are DIFFERENT purchases — keep them as written: \
"red bell pepper" stays "red bell pepper"; "boneless skinless chicken breast" \
stays "boneless skinless chicken breast"; only depluralize \
("red bell peppers" -> "red bell pepper").
- Salted vs. unsalted butter stay separate; shredded/grated cheese forms stay \
as written (e.g. "shredded cheddar" stays "shredded cheddar", not "cheddar").
- "Prepared form != raw form" — these are different products, never collapse \
one into the other: almond flour != almonds, breadcrumbs != bread, tomato \
paste != tomatoes, coconut milk != coconut, vanilla extract != vanilla beans, \
chicken broth != chicken.
- Ground vs. fresh forms of the same ingredient are different purchases \
(e.g. "ground ginger" stays "ground ginger", separate from "ginger").
- For any other novel phrasing, apply the same judgment: would a shopper buy \
a different item off the shelf for this? If yes, keep the distinction. If no \
(e.g. it's just a plural, a brand name, or an extra adjective that doesn't \
change the product), normalize to the simpler shared name.

Every input must get exactly one output, lowercase, even if it's just the \
input unchanged."""

TOOLS = [
    {
        "name": "normalize_ingredients",
        "description": "Record the canonical purchasable name for each raw ingredient string.",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "raw_name": {"type": "string"},
                            "canonical_name": {"type": "string"},
                        },
                        "required": ["raw_name", "canonical_name"],
                    },
                },
            },
            "required": ["items"],
        },
    },
]


def get_cached(raw_names: list[str]) -> dict[str, str]:
    """Look up cached canonical names for the given (already-lowercased) raw ingredient names."""
    if not raw_names:
        return {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT raw_name, canonical_name FROM ingredient_normalizations WHERE raw_name = ANY(%s)",
                (raw_names,),
            )
            return dict(cur.fetchall())


def _upsert_cache(mapping: dict[str, str]) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            for raw_name, canonical_name in mapping.items():
                cur.execute(
                    """INSERT INTO ingredient_normalizations (raw_name, canonical_name)
                       VALUES (%s, %s)
                       ON CONFLICT (raw_name) DO UPDATE SET canonical_name = EXCLUDED.canonical_name""",
                    (raw_name, canonical_name),
                )
        conn.commit()


SYSTEM_PROMPT_RECONCILE = """You reconcile grocery-shopping units and assign store \
categories for purchasable ingredients drawn from a meal plan.

For each ingredient, you're given every unit it appears in across the plan (e.g. \
"olive oil" might appear in both "tbsp" and "cup"). For each:

- Pick ONE `target_unit` suited for grocery shopping — either a count \
("unit", "clove", "slice", "can", etc.) for discrete items, or a standard \
kitchen measure ("cup", "tbsp", "tsp", "oz", "lb", "g") for everything else. \
If the ingredient only appears in one unit, that unit IS the target_unit.
- For each unit it appears in, give a numeric `multiplier` that converts a \
quantity in that unit into the target_unit (e.g. converting "tbsp" to a \
"cup" target gives multiplier 0.0625, since 1 tbsp = 1/16 cup). The unit \
that equals the target_unit gets multiplier 1.0.
- Assign one `category` — the store section a shopper would find this item in: \
"produce", "protein", "dairy", "frozen", or "pantry" (the catch-all for spices, \
oils, grains, canned goods, etc.).

Every ingredient must get exactly one category and a multiplier for every unit \
listed for it."""

TOOLS_RECONCILE = [
    {
        "name": "reconcile_units",
        "description": "Record the target shopping unit, per-unit conversion multipliers, and store category for each ingredient.",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "canonical_name": {"type": "string"},
                            "category": {
                                "type": "string",
                                "enum": ["produce", "protein", "dairy", "frozen", "pantry"],
                            },
                            "units": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "unit": {"type": "string"},
                                        "target_unit": {"type": "string"},
                                        "multiplier": {"type": "number"},
                                    },
                                    "required": ["unit", "target_unit", "multiplier"],
                                },
                            },
                        },
                        "required": ["canonical_name", "category", "units"],
                    },
                },
            },
            "required": ["items"],
        },
    },
]


def reconcile_quantities(items: list[dict]) -> tuple[dict[tuple[str, str], dict], dict | None]:
    """Reconcile shopping units and assign a store category for canonical ingredients.

    `items` is a list of {"canonical_name": str, "unit": str} pairs (one per
    distinct unit a canonical ingredient appears in across a plan).

    Returns (mapping from (canonical_name.lower(), unit.lower()) -> {target_unit,
    multiplier, category}, transcript). This step is uncached — every call makes
    an LLM call, so `transcript` is always set unless `items` is empty.
    """
    if not items:
        return {}, None

    grouped: dict[str, set[str]] = {}
    for item in items:
        grouped.setdefault(item["canonical_name"].lower(), set()).add(item["unit"].lower())

    lines = [
        f"{name}: " + ", ".join(sorted(units))
        for name, units in sorted(grouped.items())
    ]

    start = time.time()
    inputs = [{"role": "user", "content": "Reconcile units and categorize these ingredients:\n" + "\n".join(lines)}]

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT_RECONCILE,
            tools=TOOLS_RECONCILE,
            tool_choice={"type": "tool", "name": "reconcile_units"},
            messages=inputs,
        )
    except Exception as e:
        raise RuntimeError(f"Quantity reconciliation call failed: {e}") from e

    tool_use = next(b for b in response.content if b.type == "tool_use")

    mapping: dict[tuple[str, str], dict] = {}
    for entry in tool_use.input.get("items", []):
        name = entry["canonical_name"].lower()
        category = entry["category"]
        for unit_entry in entry.get("units", []):
            mapping[(name, unit_entry["unit"].lower())] = {
                "target_unit": unit_entry["target_unit"],
                "multiplier": unit_entry["multiplier"],
                "category": category,
            }

    # Every requested (name, unit) pair must resolve; fall back to identity for
    # any the model dropped so callers always get a usable entry.
    for name, units in grouped.items():
        for unit in units:
            mapping.setdefault((name, unit), {"target_unit": unit, "multiplier": 1.0, "category": "pantry"})

    latency_ms = round((time.time() - start) * 1000)
    final_history = inputs + [{"role": "assistant", "content": response.content}]
    transcript = build_transcript(
        agent_type="grocery_reconciler",
        model=MODEL,
        system=SYSTEM_PROMPT_RECONCILE,
        inputs=inputs,
        history=final_history,
        output=str(mapping),
        outcome={"reconciled": {f"{k[0]}|{k[1]}": v for k, v in mapping.items()}},
        usage={"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens},
        latency_ms=latency_ms,
    )

    return mapping, transcript


def normalize_ingredients(raw_names: list[str]) -> tuple[dict[str, str], dict | None]:
    """Map each raw ingredient name to its purchasable canonical name.

    Returns (mapping from lowercased raw_name -> canonical_name, transcript).
    transcript is None if every name was a cache hit (no LLM call made).
    """
    lowered = sorted({name.lower() for name in raw_names})
    mapping = get_cached(lowered)
    misses = [name for name in lowered if name not in mapping]

    if not misses:
        return mapping, None

    start = time.time()
    inputs = [{"role": "user", "content": "Normalize these ingredient names:\n" + "\n".join(misses)}]

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            tool_choice={"type": "tool", "name": "normalize_ingredients"},
            messages=inputs,
        )
    except Exception as e:
        raise RuntimeError(f"Ingredient normalization call failed: {e}") from e

    tool_use = next(b for b in response.content if b.type == "tool_use")
    new_mapping = {
        item["raw_name"].lower(): item["canonical_name"].lower()
        for item in tool_use.input.get("items", [])
    }
    # The model must return a canonical name for every input (no "uncertain" bucket);
    # fall back to identity for any it dropped so the cache always has an entry.
    for name in misses:
        new_mapping.setdefault(name, name)

    _upsert_cache(new_mapping)

    latency_ms = round((time.time() - start) * 1000)
    final_history = inputs + [{"role": "assistant", "content": response.content}]
    transcript = build_transcript(
        agent_type="grocery_normalizer",
        model=MODEL,
        system=SYSTEM_PROMPT,
        inputs=inputs,
        history=final_history,
        output=str(new_mapping),
        outcome={"normalized": new_mapping},
        usage={"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens},
        latency_ms=latency_ms,
    )

    mapping.update(new_mapping)
    return mapping, transcript
