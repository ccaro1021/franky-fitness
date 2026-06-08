import os
import requests
from dotenv import load_dotenv
from models import Ingredient, Meal

load_dotenv()

BASE_URL = "https://api.spoonacular.com"
API_KEY = os.getenv("SPOONACULAR_API_KEY")


def search_recipes(query: str = "", number: int = 10, **filters) -> list[Meal]:
    params = {
        "apiKey": API_KEY,
        "query": query,
        "number": number,
        "addRecipeInformation": True,
        "addRecipeNutrition": True,
        **filters,
    }
    response = requests.get(f"{BASE_URL}/recipes/complexSearch", params=params)
    response.raise_for_status()
    return [_map_to_meal(r) for r in response.json().get("results", [])]


def get_recipe(recipe_id: int) -> Meal:
    params = {
        "apiKey": API_KEY,
        "includeNutrition": True,
    }
    response = requests.get(f"{BASE_URL}/recipes/{recipe_id}/information", params=params)
    response.raise_for_status()
    return _map_to_meal(response.json())


def _get_nutrient(nutrients: list[dict], name: str) -> int:
    for n in nutrients:
        if n["name"] == name:
            return round(n["amount"])
    return 0


def _map_to_meal(data: dict) -> Meal:
    servings = data.get("servings") or 1
    nutrients = data.get("nutrition", {}).get("nutrients", [])

    ingredients = [
        Ingredient(
            name=ing.get("nameClean") or ing["name"],
            quantity_per_serving=round(ing["amount"] / servings, 2),
            unit=ing.get("unit") or "unit",
        )
        for ing in data.get("extendedIngredients", [])
    ]

    steps = []
    for section in data.get("analyzedInstructions", []):
        for step in section.get("steps", []):
            steps.append(f"{step['number']}. {step['step']}")
    recipe_text = "\n".join(steps) if steps else data.get("instructions", "") or ""

    return Meal(
        name=data["title"],
        calories_per_serving=_get_nutrient(nutrients, "Calories"),
        protein_g=_get_nutrient(nutrients, "Protein"),
        carbs_g=_get_nutrient(nutrients, "Carbohydrates"),
        fat_g=_get_nutrient(nutrients, "Fat"),
        recipe=recipe_text,
        ingredients=ingredients,
        spoonacular_id=data.get("id"),
    )
