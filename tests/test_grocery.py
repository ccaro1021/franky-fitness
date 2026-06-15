"""Unit tests for grocery list generation (summing, structure).

Normalization (raw ingredient name -> purchasable canonical name) and unit/category
reconciliation are now LLM-backed steps (backend/grocery_agent.py) — these tests
stub those steps by feeding `canonical_name`, `unit`, and `category` directly on
each ingredient, and assert generate_grocery_list's summing logic behaves
correctly given that pre-reconciled data.

Run from the repo root: `python -m unittest tests.test_grocery`
"""

import unittest

from grocery import generate_grocery_list


def _plan(*ingredients: dict) -> dict:
    """Wrap a list of ingredient dicts into a single-meal plan for testing."""
    return {"meals": [{"ingredients": list(ingredients)}]}


def _ing(
    name: str,
    quantity: float = 1.0,
    unit: str = "unit",
    canonical_name: str | None = None,
    category: str | None = None,
) -> dict:
    """Build one ingredient dict in the shape generate_grocery_list expects."""
    ingredient = {
        "name": name,
        "canonical_name": canonical_name if canonical_name is not None else name,
        "quantity_per_serving": quantity,
        "unit": unit,
    }
    if category is not None:
        ingredient["category"] = category
    return ingredient


def _by_name(items) -> dict[str, object]:
    """Index a grocery list by item name for easy assertions."""
    return {item.name: item for item in items}


class CanonicalNameMergingTest(unittest.TestCase):
    """Ingredients sharing a canonical_name should collapse and sum."""

    def test_egg_components_merge_into_eggs(self):
        items = generate_grocery_list(
            _plan(
                _ing("egg yolks", 2, canonical_name="eggs"),
                _ing("egg whites", 3, canonical_name="eggs"),
            )
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "eggs")
        self.assertEqual(items[0].total_quantity, 5)

    def test_plural_and_synonym_normalize_to_same_base(self):
        items = generate_grocery_list(
            _plan(
                _ing("tomatoes", 2, canonical_name="tomato"),
                _ing("tomato", 1, canonical_name="tomato"),
            )
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "tomato")
        self.assertEqual(items[0].total_quantity, 3)

    def test_pantry_synonyms_collapse(self):
        items = generate_grocery_list(
            _plan(
                _ing("extra virgin olive oil", 1, "tbsp", canonical_name="olive oil"),
                _ing("evoo", 2, "tbsp", canonical_name="olive oil"),
            )
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "olive oil")
        self.assertEqual(items[0].total_quantity, 3)

    def test_fresh_herb_drops_redundant_descriptor(self):
        items = generate_grocery_list(
            _plan(
                _ing("fresh basil", 1, "tbsp", canonical_name="basil"),
                _ing("basil", 2, "tbsp", canonical_name="basil"),
            )
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "basil")
        self.assertEqual(items[0].total_quantity, 3)


class NoCollapseInvariantTest(unittest.TestCase):
    """Distinctions that change what you actually buy must NOT be merged."""

    def test_bell_pepper_colors_stay_distinct(self):
        items = generate_grocery_list(
            _plan(_ing("red bell pepper"), _ing("green bell pepper"))
        )
        names = set(_by_name(items))
        self.assertEqual(names, {"red bell pepper", "green bell pepper"})

    def test_dried_herb_distinct_from_fresh(self):
        items = generate_grocery_list(
            _plan(
                _ing("fresh basil", 1, "tbsp", canonical_name="basil"),
                _ing("dried basil", 1, "tsp"),
            )
        )
        names = set(_by_name(items))
        self.assertEqual(names, {"basil", "dried basil"})

    def test_ground_ginger_distinct_from_fresh_ginger(self):
        # The dried spice and the produce root are different purchases.
        items = generate_grocery_list(
            _plan(
                _ing("ground ginger", 1, "tsp"),
                _ing("fresh ginger", 1, "tbsp", canonical_name="ginger"),
            )
        )
        names = set(_by_name(items))
        self.assertEqual(names, {"ground ginger", "ginger"})

    def test_salted_and_unsalted_butter_stay_separate(self):
        items = generate_grocery_list(
            _plan(_ing("salted butter", 1, "tbsp"), _ing("unsalted butter", 1, "tbsp"))
        )
        names = set(_by_name(items))
        self.assertEqual(names, {"salted butter", "unsalted butter"})

    def test_boneless_skinless_descriptor_preserved(self):
        items = generate_grocery_list(
            _plan(_ing("boneless skinless chicken breasts", 2, canonical_name="boneless skinless chicken breast"))
        )
        self.assertEqual(items[0].name, "boneless skinless chicken breast")

    def test_minced_garlic_kept_as_written(self):
        items = generate_grocery_list(_plan(_ing("minced garlic", 1, "tsp")))
        self.assertEqual(items[0].name, "minced garlic")

    def test_shredded_cheese_form_kept(self):
        items = generate_grocery_list(_plan(_ing("shredded cheddar", 1, "cup")))
        self.assertEqual(items[0].name, "shredded cheddar")

    def test_greek_yogurt_is_its_own_base_item(self):
        items = generate_grocery_list(
            _plan(
                _ing("plain greek yogurt", 1, "cup", canonical_name="greek yogurt"),
                _ing("yogurt", 1, "cup"),
            )
        )
        names = set(_by_name(items))
        self.assertEqual(names, {"greek yogurt", "yogurt"})

    def test_heavy_cream_base_item(self):
        items = generate_grocery_list(
            _plan(
                _ing("heavy whipping cream", 1, "cup", canonical_name="heavy cream"),
                _ing("heavy cream", 1, "cup"),
            )
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "heavy cream")
        self.assertEqual(items[0].total_quantity, 2)


class StructuralTest(unittest.TestCase):
    """Structural guarantees about generate_grocery_list itself."""

    def test_falls_back_to_raw_name_when_canonical_name_missing(self):
        items = generate_grocery_list(_plan({"name": "kale", "quantity_per_serving": 1, "unit": "cup"}))
        self.assertEqual(items[0].name, "kale")

    def test_discrete_units_round_up(self):
        items = generate_grocery_list(
            _plan(
                _ing("egg", 0.5, "unit", canonical_name="eggs"),
                _ing("egg", 0.6, "unit", canonical_name="eggs"),
            )
        )
        self.assertEqual(items[0].total_quantity, 2)

    def test_category_passes_through_from_ingredient_data(self):
        items = generate_grocery_list(_plan(_ing("egg yolks", 2, canonical_name="eggs", category="protein")))
        self.assertEqual(items[0].category, "protein")

    def test_category_defaults_to_pantry_when_missing(self):
        items = generate_grocery_list(_plan(_ing("kale", 1, "cup")))
        self.assertEqual(items[0].category, "pantry")


if __name__ == "__main__":
    unittest.main()
