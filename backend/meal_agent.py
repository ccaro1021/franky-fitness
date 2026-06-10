import time
from anthropic import Anthropic
from dotenv import load_dotenv
from spoonacular import get_recipe, search_recipes

load_dotenv()

client = Anthropic()

_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
_MEAL_ORDER = ['breakfast', 'lunch', 'dinner', 'snack']

TOOLS = [
    {
        "name": "search_meals",
        "description": (
            "Search for real recipes matching nutritional goals and preferences. "
            "Use this to find specific meals before including them in a plan. "
            "Returns meal names, calories, and macros per serving."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term, e.g. 'grilled chicken', 'high protein breakfast', 'low carb dinner'",
                },
                "max_calories": {
                    "type": "integer",
                    "description": "Maximum calories per serving",
                },
                "min_protein": {
                    "type": "integer",
                    "description": "Minimum protein in grams per serving",
                },
                "number": {
                    "type": "integer",
                    "description": "Number of results to return (1–10, default 5)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_recipe",
        "description": (
            "Fetch the full recipe for a meal — ingredients and step-by-step instructions. "
            "Use this when the user asks how to make a specific meal. "
            "Prefer passing spoonacular_id from the saved plan; fall back to meal_name if needed."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "spoonacular_id": {
                    "type": "integer",
                    "description": "Spoonacular recipe ID from the meal plan",
                },
                "meal_name": {
                    "type": "string",
                    "description": "Meal name to search by, used only if spoonacular_id is not available",
                },
            },
        },
    },
    {
        "name": "finalize_meal_plan",
        "description": (
            "Call this once you have assembled the complete weekly meal plan. "
            "Include every meal for every day before calling this. "
            "Use calorie and macro values from your search_meals results, not estimates."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "meals": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "day": {"type": "string", "description": "Day of the week, e.g. Monday"},
                            "meal_type": {
                                "type": "string",
                                "enum": ["breakfast", "lunch", "dinner", "snack"],
                            },
                            "name": {"type": "string"},
                            "calories": {"type": "integer"},
                            "protein_g": {"type": "integer"},
                            "carbs_g": {"type": "integer"},
                            "fat_g": {"type": "integer"},
                            "spoonacular_id": {"type": "integer"},
                        },
                        "required": ["day", "meal_type", "name", "calories", "protein_g", "carbs_g", "fat_g"],
                    },
                },
                "notes": {
                    "type": "string",
                    "description": "Coaching notes, substitutions, or tips for the week",
                },
            },
            "required": ["meals"],
        },
    },
]


def _format_plan_for_prompt(plan: dict) -> str:
    by_day: dict[str, list] = {}
    for meal in plan.get("meals", []):
        by_day.setdefault(meal["day"], []).append(meal)

    lines = []
    for day in _DAYS:
        if day not in by_day:
            continue
        lines.append(day)
        sorted_meals = sorted(
            by_day[day],
            key=lambda m: _MEAL_ORDER.index(m["meal_type"]) if m["meal_type"] in _MEAL_ORDER else 99,
        )
        for meal in sorted_meals:
            sid = f" (ID: {meal['spoonacular_id']})" if meal.get("spoonacular_id") else ""
            lines.append(
                f"  {meal['meal_type'].capitalize()}: {meal['name']}{sid} — "
                f"{meal['calories']} kcal | {meal['protein_g']}g protein | "
                f"{meal['carbs_g']}g carbs | {meal['fat_g']}g fat"
            )
    return "\n".join(lines)


def _build_system_prompt(profile: dict, current_plan: dict | None = None) -> str:
    restrictions = ", ".join(profile["dietary_restrictions"]) if profile["dietary_restrictions"] else "none"
    goals = ", ".join(profile["fitness_goals"])
    notes = profile.get("notes", "")

    prompt = f"""You are Franky, a meal planning assistant for {profile['name']}.

{profile['name']}'s profile:
- Dietary restrictions: {restrictions}
- Fitness goals: {goals}
{f"- Notes: {notes}" if notes else ""}

When building a weekly meal plan:
1. Use search_meals to find real recipes — never invent calorie or macro numbers.
2. Search for breakfast, lunch, and dinner options separately so you have real data for each.
3. Plan all 7 days before calling finalize_meal_plan.
4. For fat loss + muscle building, target high protein (at least 30g per meal), moderate carbs, and controlled calories.
5. Avoid anything that violates the person's dietary restrictions.
6. Once the full plan is assembled, call finalize_meal_plan with structured data, then summarize it conversationally.

If you need clarifying information (calorie target, foods to avoid, cooking time available), ask before generating the plan. One focused question at a time.

You are a coach, not a doctor. For medical concerns, recommend consulting a healthcare professional."""

    if current_plan:
        plan_text = _format_plan_for_prompt(current_plan)
        prompt += f"""

{profile['name']}'s current saved meal plan:
{plan_text}

When {profile['name']} asks how to make a meal, use get_recipe with that meal's Spoonacular ID from the plan above. If they refer to a meal by day or type (e.g. "Monday's dinner"), look up the correct ID from the plan."""
    else:
        prompt += f"\n\n{profile['name']} has no saved meal plan yet this week."

    return prompt


def _run_tool(name: str, inputs: dict) -> tuple[str, dict | None]:
    """Returns (text_for_agent, structured_data_for_frontend)."""
    if name == "search_meals":
        filters = {}
        if "max_calories" in inputs:
            filters["maxCalories"] = inputs["max_calories"]
        if "min_protein" in inputs:
            filters["minProtein"] = inputs["min_protein"]

        try:
            meals = search_recipes(
                query=inputs.get("query", ""),
                number=inputs.get("number", 5),
                **filters,
            )
        except Exception as e:
            return f"Recipe search is temporarily unavailable: {e}", None

        if not meals:
            return "No recipes found for that search.", None

        lines = []
        for meal in meals:
            lines.append(
                f"- {meal.name} (ID: {meal.spoonacular_id}) | {meal.calories_per_serving} kcal | "
                f"{meal.protein_g}g protein | {meal.carbs_g}g carbs | {meal.fat_g}g fat"
            )
        return "\n".join(lines), None

    if name == "get_recipe":
        spoonacular_id = inputs.get("spoonacular_id")
        meal_name = inputs.get("meal_name", "")

        try:
            if spoonacular_id:
                meal = get_recipe(spoonacular_id)
            else:
                results = search_recipes(query=meal_name, number=1)
                if not results:
                    return f"Could not find a recipe for '{meal_name}'.", None
                meal = results[0]
                if meal.spoonacular_id:
                    meal = get_recipe(meal.spoonacular_id)

            lines = [
                f"{meal.name}",
                f"Per serving: {meal.calories_per_serving} kcal | {meal.protein_g}g protein | "
                f"{meal.carbs_g}g carbs | {meal.fat_g}g fat",
                "",
                "Ingredients:",
            ]
            for ing in meal.ingredients:
                lines.append(f"  - {ing.quantity_per_serving} {ing.unit} {ing.name}")
            lines += ["", "Instructions:", meal.recipe]

            return "\n".join(lines), meal.model_dump()

        except Exception as e:
            return f"Could not retrieve recipe: {e}", None

    if name == "finalize_meal_plan":
        for meal in inputs.get("meals", []):
            spoonacular_id = meal.get("spoonacular_id")
            if spoonacular_id:
                try:
                    recipe = get_recipe(spoonacular_id)
                    meal["ingredients"] = [ing.model_dump() for ing in recipe.ingredients]
                except Exception:
                    meal["ingredients"] = []
            else:
                meal["ingredients"] = []
        return "Meal plan finalized.", inputs

    return f"Unknown tool: {name}", None


def run_meal_agent(
    messages: list[dict],
    profile: dict,
    current_plan: dict | None = None,
) -> dict:
    """
    Run the meal planning agent for one conversation turn.

    Args:
        messages: Full conversation history (role/content pairs from the frontend)
        profile: User profile from profiles.py
        current_plan: Most recently saved meal plan for this person, injected as context

    Returns:
        message, meal_plan, recipe, input_tokens, output_tokens, latency_ms
    """
    start = time.time()
    input_tokens = 0
    output_tokens = 0
    meal_plan: dict | None = None
    recipe: dict | None = None

    system = _build_system_prompt(profile, current_plan)
    history = list(messages)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            messages=history,
        )
    except Exception as e:
        raise RuntimeError(f"Agent call failed: {e}") from e

    input_tokens += response.usage.input_tokens
    output_tokens += response.usage.output_tokens

    while response.stop_reason == "tool_use":
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        history.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tool_use in tool_uses:
            result_text, result_data = _run_tool(tool_use.name, tool_use.input)

            if tool_use.name == "finalize_meal_plan":
                meal_plan = result_data

            if tool_use.name == "get_recipe" and result_data:
                recipe = result_data

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result_text,
            })

        history.append({"role": "user", "content": tool_results})

        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=system,
                tools=TOOLS,
                messages=history,
            )
        except Exception as e:
            raise RuntimeError(f"Agent call failed: {e}") from e

        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens

    message = next(b.text for b in response.content if hasattr(b, "text"))
    latency_ms = round((time.time() - start) * 1000)

    return {
        "message": message,
        "meal_plan": meal_plan,
        "recipe": recipe,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": latency_ms,
    }
