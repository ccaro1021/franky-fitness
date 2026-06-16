from pydantic import BaseModel


class Ingredient(BaseModel):
    name: str
    quantity_per_serving: float  # amount per person per meal
    unit: str                    # "oz", "cups", "tbsp", "cloves", "pieces", etc.


class Meal(BaseModel):
    name: str
    calories_per_serving: int    # per person
    protein_g: int               # grams per person
    carbs_g: int                 # grams per person
    fat_g: int                   # grams per person
    recipe: str
    ingredients: list[Ingredient]
    spoonacular_id: int | None = None


class GroceryItem(BaseModel):
    name: str
    total_quantity: float
    unit: str
    category: str = "pantry"


class Exercise(BaseModel):
    id: str
    name: str
    body_part: str
    equipment: str
    target_muscle: str
    secondary_muscles: list[str]
    instructions: list[str]
    gif_url: str             # for future UI
