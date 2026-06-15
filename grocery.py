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
    "fresh ginger": "ginger",
    "chicken stock": "chicken broth",
    "vegetable stock": "vegetable broth",
    "beef stock": "beef broth",

    # More singular/plural and varietal normalization for produce
    # Pepper color is a distinct purchase, so only depluralize within each color.
    "bell peppers": "bell pepper",
    "red bell peppers": "red bell pepper",
    "green bell peppers": "green bell pepper",
    "yellow bell peppers": "yellow bell pepper",
    "jalapeno": "jalapeño",
    "jalapenos": "jalapeño",
    "jalapeños": "jalapeño",
    "shallots": "shallot",
    "zucchinis": "zucchini",
    "apples": "apple",
    "bananas": "banana",
    "avocados": "avocado",
    "strawberries": "strawberry",
    "blueberries": "blueberry",
    "raspberries": "raspberry",
    "blackberries": "blackberry",
    "sweet potatoes": "sweet potato",

    # Fresh herbs normalize to the base produce item; dried herbs are a
    # separate spice-aisle purchase, so they keep the "dried" descriptor.
    "fresh basil": "basil",
    "dried basil": "dried basil",
    "fresh cilantro": "cilantro",
    "fresh parsley": "parsley",
    "dried parsley": "dried parsley",
    "fresh thyme": "thyme",
    "dried thyme": "dried thyme",
    "fresh rosemary": "rosemary",
    "dried rosemary": "dried rosemary",
    "fresh oregano": "oregano",
    "dried oregano": "dried oregano",
    "fresh dill": "dill",
    "fresh mint": "mint",
    "fresh chives": "chives",

    # Dairy synonyms — milk fat content collapses to one carton; salted vs.
    # unsalted butter stay distinct because it changes which stick you buy.
    "whole milk": "milk",
    "skim milk": "milk",
    "2% milk": "milk",
    "low-fat milk": "milk",
    "plain greek yogurt": "greek yogurt",
    "plain yogurt": "yogurt",
    "heavy whipping cream": "heavy cream",
    # Drop a redundant "cheese" suffix, but keep any shredded/grated form as
    # written — pre-shredded is a different purchase from a block.
    "parmesan cheese": "parmesan",
    "cheddar cheese": "cheddar",
    "mozzarella cheese": "mozzarella",

    # Protein cut/size normalization — only depluralize; "boneless skinless"
    # is a real cut distinction, so it stays as a descriptor.
    "chicken breasts": "chicken breast",
    "boneless skinless chicken breasts": "boneless skinless chicken breast",
    "chicken thighs": "chicken thigh",
    "boneless skinless chicken thighs": "boneless skinless chicken thigh",
    "large eggs": "eggs",
    "large egg": "eggs",

    # Spice/condiment synonyms
    "crushed red pepper": "red pepper flakes",
    "crushed red pepper flakes": "red pepper flakes",
    "cayenne pepper": "cayenne",
    "ground cumin": "cumin",
    "ground cinnamon": "cinnamon",
    "low sodium soy sauce": "soy sauce",
    "reduced sodium soy sauce": "soy sauce",
    "light brown sugar": "brown sugar",
    "dark brown sugar": "brown sugar",
    "confectioners sugar": "powdered sugar",
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
