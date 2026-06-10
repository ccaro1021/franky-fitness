import math

from models import GroceryItem

_INGREDIENT_ALIASES: dict[str, str] = {
    # Egg components — you buy whole eggs, not yolks/whites separately
    "egg yolk": "eggs",
    "egg yolks": "eggs",
    "egg white": "eggs",
    "egg whites": "eggs",
    "egg": "eggs",

    # Singular/plural normalization for common produce
    "onions": "onion",
    "tomatoes": "tomato",
    "potatoes": "potato",
    "carrots": "carrot",
    "scallions": "scallion",
    "green onions": "green onion",
    "cucumbers": "cucumber",
    "mushrooms": "mushroom",
    "lemons": "lemon",
    "limes": "lime",

    # Pantry staple synonyms — same shopping item, different recipe phrasing
    "extra virgin olive oil": "olive oil",
    "evoo": "olive oil",
    "kosher salt": "salt",
    "sea salt": "salt",
    "table salt": "salt",
    "ground black pepper": "black pepper",
    "ground pepper": "black pepper",
    "all-purpose flour": "flour",
    "all purpose flour": "flour",
    "granulated sugar": "sugar",
    "white sugar": "sugar",
    "garlic clove": "garlic",
    "garlic cloves": "garlic",
    "minced garlic": "garlic",
    "fresh ginger": "ginger",
    "chicken stock": "chicken broth",
    "vegetable stock": "vegetable broth",
    "beef stock": "beef broth",
}

# Units for items sold individually — round up to a whole shoppable count.
_DISCRETE_UNITS = {"unit", "large", "small", "medium", "whole"}

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "produce": [
        "lettuce", "spinach", "kale", "arugula", "tomato", "onion", "garlic", "pepper",
        "broccoli", "cauliflower", "carrot", "cucumber", "avocado", "lemon", "lime",
        "apple", "banana", "berry", "berries", "potato", "zucchini", "mushroom",
        "celery", "cilantro", "parsley", "basil", "ginger", "scallion", "green onion",
        "cabbage", "squash", "corn",
    ],
    "protein": [
        "chicken", "beef", "pork", "turkey", "salmon", "tuna", "shrimp", "tofu",
        "egg", "bacon", "sausage", "steak", "tilapia", "cod",
    ],
    "dairy": [
        "milk", "cheese", "yogurt", "butter", "cream", "parmesan", "mozzarella", "cheddar",
    ],
    "frozen": ["frozen"],
}


def categorize_ingredient(name: str) -> str:
    """Map an ingredient name to a store-section category via keyword lookup."""
    lowered = name.lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return "pantry"


def generate_grocery_list(plan: dict) -> list[GroceryItem]:
    """Sum ingredient quantities across a saved meal plan and categorize each item."""
    totals: dict[tuple[str, str], GroceryItem] = {}
    for meal in plan.get("meals", []):
        for ingredient in meal.get("ingredients", []):
            name = _INGREDIENT_ALIASES.get(ingredient["name"].lower(), ingredient["name"])
            unit = ingredient.get("unit", "unit")
            quantity = ingredient.get("quantity_per_serving", 0)
            key = (name.lower(), unit)
            if key in totals:
                totals[key].total_quantity += quantity
            else:
                totals[key] = GroceryItem(
                    name=name,
                    total_quantity=quantity,
                    unit=unit,
                    category=categorize_ingredient(name),
                )

    for item in totals.values():
        if item.unit in _DISCRETE_UNITS:
            item.total_quantity = math.ceil(item.total_quantity)

    return list(totals.values())
