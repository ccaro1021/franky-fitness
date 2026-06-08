from pydantic import BaseModel


class Person(BaseModel):
    name: str
    age: int
    weight_lbs: float
    height_inches: float
    bmi: float
    goals: list[str]           # e.g. ["lose fat", "build muscle"]
    health_concerns: list[str] # e.g. ["high blood pressure", "diabetes risk"]


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


class PlannedMeal(BaseModel):
    meal: Meal
    times_per_week: int


class GroceryItem(BaseModel):
    name: str
    total_quantity: float
    unit: str


class Exercise(BaseModel):
    id: str
    name: str
    body_part: str
    equipment: str
    target_muscle: str
    secondary_muscles: list[str]
    instructions: list[str]
    gif_url: str             # for future UI


class WeeklyPlan(BaseModel):
    planned_meals: list[PlannedMeal]
    people: int = 2  # defaults to a couple

    def grocery_list(self) -> list[GroceryItem]:
        totals: dict[str, GroceryItem] = {}
        for entry in self.planned_meals:
            for ingredient in entry.meal.ingredients:
                total = ingredient.quantity_per_serving * self.people * entry.times_per_week
                key = ingredient.name.lower()
                if key in totals:
                    totals[key].total_quantity += total
                else:
                    totals[key] = GroceryItem(
                        name=ingredient.name,
                        total_quantity=total,
                        unit=ingredient.unit,
                    )
        return list(totals.values())
