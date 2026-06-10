from models import GroceryItem

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
            name = ingredient["name"]
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
    return list(totals.values())
