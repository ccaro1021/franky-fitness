"""Unit tests for the grocery alias table and its effect on list generation.

Run from the repo root: `python -m unittest tests.test_grocery`
The tests exercise the alias table through the public `generate_grocery_list`
interface so they stay valid if the table's internals are refactored.
"""

import unittest

from grocery import _INGREDIENT_ALIASES, categorize_ingredient, generate_grocery_list


def _plan(*ingredients: dict) -> dict:
    """Wrap a list of ingredient dicts into a single-meal plan for testing."""
    return {"meals": [{"ingredients": list(ingredients)}]}


def _ing(name: str, quantity: float = 1.0, unit: str = "unit") -> dict:
    """Build one ingredient dict in the shape generate_grocery_list expects."""
    return {"name": name, "quantity_per_serving": quantity, "unit": unit}


def _by_name(items) -> dict[str, object]:
    """Index a grocery list by item name for easy assertions."""
    return {item.name: item for item in items}


class AliasMergingTest(unittest.TestCase):
    """Variants that name the same shoppable item should collapse and sum."""

    def test_egg_components_merge_into_eggs(self):
        items = generate_grocery_list(
            _plan(_ing("egg yolks", 2), _ing("egg whites", 3))
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "eggs")
        self.assertEqual(items[0].total_quantity, 5)

    def test_plural_and_synonym_normalize_to_same_base(self):
        items = generate_grocery_list(
            _plan(_ing("tomatoes", 2), _ing("tomato", 1))
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "tomato")
        self.assertEqual(items[0].total_quantity, 3)

    def test_pantry_synonyms_collapse(self):
        items = generate_grocery_list(
            _plan(
                _ing("extra virgin olive oil", 1, "tbsp"),
                _ing("evoo", 2, "tbsp"),
            )
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "olive oil")
        self.assertEqual(items[0].total_quantity, 3)

    def test_fresh_herb_drops_redundant_descriptor(self):
        items = generate_grocery_list(
            _plan(_ing("fresh basil", 1, "tbsp"), _ing("basil", 2, "tbsp"))
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

    def test_bell_pepper_colors_only_depluralize(self):
        self.assertEqual(_INGREDIENT_ALIASES["red bell peppers"], "red bell pepper")
        self.assertNotIn("red bell pepper", _INGREDIENT_ALIASES)

    def test_dried_herb_distinct_from_fresh(self):
        items = generate_grocery_list(
            _plan(_ing("fresh basil", 1, "tbsp"), _ing("dried basil", 1, "tsp"))
        )
        names = set(_by_name(items))
        self.assertEqual(names, {"basil", "dried basil"})

    def test_ground_ginger_distinct_from_fresh_ginger(self):
        # The dried spice and the produce root are different purchases.
        items = generate_grocery_list(
            _plan(_ing("ground ginger", 1, "tsp"), _ing("fresh ginger", 1, "tbsp"))
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
        items = generate_grocery_list(_plan(_ing("boneless skinless chicken breasts", 2)))
        self.assertEqual(items[0].name, "boneless skinless chicken breast")

    def test_minced_garlic_kept_as_written(self):
        self.assertNotIn("minced garlic", _INGREDIENT_ALIASES)
        items = generate_grocery_list(_plan(_ing("minced garlic", 1, "tsp")))
        self.assertEqual(items[0].name, "minced garlic")

    def test_shredded_cheese_form_kept(self):
        self.assertNotIn("shredded cheddar", _INGREDIENT_ALIASES)
        items = generate_grocery_list(_plan(_ing("shredded cheddar", 1, "cup")))
        self.assertEqual(items[0].name, "shredded cheddar")

    def test_greek_yogurt_is_its_own_base_item(self):
        items = generate_grocery_list(
            _plan(_ing("plain greek yogurt", 1, "cup"), _ing("yogurt", 1, "cup"))
        )
        names = set(_by_name(items))
        self.assertEqual(names, {"greek yogurt", "yogurt"})

    def test_heavy_cream_base_item(self):
        items = generate_grocery_list(
            _plan(_ing("heavy whipping cream", 1, "cup"), _ing("heavy cream", 1, "cup"))
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].name, "heavy cream")
        self.assertEqual(items[0].total_quantity, 2)


class AliasTableIntegrityTest(unittest.TestCase):
    """Structural guarantees about the table itself."""

    def test_keys_are_lowercase(self):
        # Lookups use ingredient["name"].lower(), so an uppercase key is dead.
        for key in _INGREDIENT_ALIASES:
            self.assertEqual(key, key.lower(), f"alias key not lowercase: {key!r}")

    def test_values_resolve_in_one_hop(self):
        # generate_grocery_list resolves only one hop, so an alias value must be
        # a terminal base item. An identity self-map (value == key) is fine; a
        # value pointing at a *different* key would silently not fully resolve.
        chained = {
            key: value
            for key, value in _INGREDIENT_ALIASES.items()
            if value != key and value in _INGREDIENT_ALIASES
        }
        self.assertEqual(
            chained,
            {},
            f"alias values that are also other keys need multi-hop resolution: {chained}",
        )

    def test_aliased_item_categorizes_same_as_its_base(self):
        # Normalization must not change which store section an item lands in.
        items = generate_grocery_list(_plan(_ing("egg yolks", 2)))
        self.assertEqual(items[0].category, categorize_ingredient("eggs"))


if __name__ == "__main__":
    unittest.main()
