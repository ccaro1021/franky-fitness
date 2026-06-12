"""Seed eval Tasks: {id, description, inputs, profile, success_criteria, graders, source}.

Drawn from real failures and core behaviors for this project (see
docs/SLICE_8_OBSERVABILITY_EVALS_PLAN.md). Balanced positive/negative —
clarify_before_plan is the negative case.
"""

from evals.graders import (
    emitted_no_plan,
    equipment_subset,
    every_meal_min_protein,
    judge,
    macros_trace_to_search,
    no_restricted_ingredients,
    plan_has_n_days,
    routed_to,
)

DEFAULT_PROFILE = {
    "name": "Eval User",
    "height_inches": None,
    "weight_lbs": None,
    "target_weight_lbs": None,
    "dietary_restrictions": [],
    "fitness_goals": ["general fitness"],
    "notes": "",
    "bmi": None,
}

SAMPLE_MEAL_PLAN = {
    "meals": [
        {
            "day": "Monday",
            "meal_type": "dinner",
            "name": "Grilled Chicken with Rice and Broccoli",
            "calories": 550,
            "protein_g": 45,
            "carbs_g": 50,
            "fat_g": 12,
            "spoonacular_id": 716429,
            "ingredients": [],
        },
    ],
    "notes": "Sample plan seeded for eval fixtures.",
}


def _user(content: str) -> list[dict]:
    return [{"role": "user", "content": content}]


TASKS = [
    {
        "id": "meal_high_protein",
        "description": "Build me a high-protein weekly meal plan",
        "inputs": _user(
            "Build me a high-protein weekly meal plan targeting about 2200 calories a day. "
            "I don't have any major dietary restrictions."
        ),
        "profile": DEFAULT_PROFILE,
        "current_meal_plan": None,
        "current_workout_plan": None,
        "success_criteria": "Routes to meal; finalized plan covers all 7 days; "
        "every breakfast/lunch/dinner has at least 30g protein.",
        "graders": [
            routed_to("meal"),
            plan_has_n_days(7),
            every_meal_min_protein(30, meal_types=["breakfast", "lunch", "dinner"]),
        ],
        "source": "core behavior",
    },
    {
        "id": "meal_vegetarian_compliance",
        "description": "Vegetarian profile asks for a weekly meal plan",
        "inputs": _user("Plan my meals for the week, targeting about 2000 calories a day."),
        "profile": {**DEFAULT_PROFILE, "dietary_restrictions": ["vegetarian"]},
        "current_meal_plan": None,
        "current_workout_plan": None,
        "success_criteria": "Routes to meal; the finalized plan contains no meat or fish ingredients.",
        "graders": [routed_to("meal"), no_restricted_ingredients(["vegetarian"])],
        "source": "dietary-restriction risk",
    },
    {
        "id": "exercise_dumbbell_only",
        "description": "3-day dumbbell-only workout program",
        "inputs": _user(
            "I want a 3-day-per-week workout program. I only have dumbbells at home, no other equipment. "
            "No injuries to worry about."
        ),
        "profile": DEFAULT_PROFILE,
        "current_meal_plan": None,
        "current_workout_plan": None,
        "success_criteria": "Routes to exercise; finalized plan covers exactly 3 training days; "
        "every exercise uses only dumbbell or body weight equipment.",
        "graders": [
            routed_to("exercise"),
            plan_has_n_days(3),
            equipment_subset(["dumbbell", "body weight"]),
        ],
        "source": "core behavior",
    },
    {
        "id": "routing_recipe_howto",
        "description": "Recipe how-to question with a saved meal plan in context",
        "inputs": _user("How do I make Monday's dinner?"),
        "profile": DEFAULT_PROFILE,
        "current_meal_plan": SAMPLE_MEAL_PLAN,
        "current_workout_plan": None,
        "success_criteria": "Routes to meal, not exercise.",
        "graders": [routed_to("meal")],
        "source": "routing correctness",
    },
    {
        "id": "routing_workout_split",
        "description": "Asks for a push/pull/legs split",
        "inputs": _user("What's a good push/pull/legs split for someone training 6 days a week?"),
        "profile": DEFAULT_PROFILE,
        "current_meal_plan": None,
        "current_workout_plan": None,
        "success_criteria": "Routes to exercise.",
        "graders": [routed_to("exercise")],
        "source": "routing correctness",
    },
    {
        "id": "clarify_before_plan",
        "description": "Vague request should prompt one clarifying question, not a finalized plan (negative case)",
        "inputs": _user("Help me eat better."),
        "profile": DEFAULT_PROFILE,
        "current_meal_plan": None,
        "current_workout_plan": None,
        "success_criteria": "Routes to meal; asks exactly one focused clarifying question; "
        "does NOT emit a finalized meal plan.",
        "graders": [
            routed_to("meal"),
            emitted_no_plan(),
            judge(
                "The agent's reply asks exactly one focused clarifying question "
                "and does not present a finalized weekly meal plan."
            ),
        ],
        "source": "balanced/negative",
    },
    {
        "id": "no_invented_macros",
        "description": "Asks for high-protein breakfast ideas without finalizing a plan",
        "inputs": _user("Give me a couple of high protein breakfast ideas, just suggestions for now."),
        "profile": DEFAULT_PROFILE,
        "current_meal_plan": None,
        "current_workout_plan": None,
        "success_criteria": "Routes to meal; any calorie/macro numbers cited trace back to a search_meals result.",
        "graders": [routed_to("meal"), macros_trace_to_search()],
        "source": "never invent macros prompt rule",
    },
]


def get_task(task_id: str) -> dict:
    """Return the Task with the given id, or raise KeyError."""
    for task in TASKS:
        if task["id"] == task_id:
            return task
    raise KeyError(f"Unknown task id: {task_id}")
