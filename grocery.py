import math

from models import GroceryItem

# Units for items sold individually — round up to a whole shoppable count.
_DISCRETE_UNITS = {"unit", "large", "small", "medium", "whole"}


def generate_grocery_list(plan: dict) -> list[GroceryItem]:
    """Sum ingredient quantities across a saved meal plan, grouped by canonical name and unit.

    Each ingredient's `unit`, `quantity_per_serving`, and `category` are expected
    to already be reconciled (see backend.grocery_agent.reconcile_quantities) so
    that summing within a canonical name is just addition.
    """
    totals: dict[tuple[str, str], GroceryItem] = {}
    for meal in plan.get("meals", []):
        for ingredient in meal.get("ingredients", []):
            name = ingredient.get("canonical_name", ingredient["name"])
            unit = ingredient.get("unit", "unit")
            quantity = ingredient.get("quantity_per_serving", 0)
            category = ingredient.get("category", "pantry")
            key = (name.lower(), unit)
            if key in totals:
                totals[key].total_quantity += quantity
            else:
                totals[key] = GroceryItem(
                    name=name,
                    total_quantity=quantity,
                    unit=unit,
                    category=category,
                )

    for item in totals.values():
        if item.unit in _DISCRETE_UNITS:
            item.total_quantity = math.ceil(item.total_quantity)

    return list(totals.values())
