import json
import anthropic
from datetime import date
from dotenv import load_dotenv
from anthropic import Anthropic
from spoonacular import search_recipes
from exercisedb import search_exercises
from models import MonthlyPlan, WorkoutDay, PlannedExercise

load_dotenv()
client = Anthropic()
conversation_history = []

with open("system_prompt.txt", "r") as f:
    SYSTEM_PROMPT = f.read()

TOOLS = [
    {
        "name": "search_meals",
        "description": (
            "Search for real recipes that match nutritional goals and preferences. "
            "Use this whenever the user asks for meal suggestions, recipe ideas, or meal planning help. "
            "Returns meal names, calories, and macros per serving."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term, e.g. 'grilled chicken', 'low carb dinner', 'high protein breakfast'",
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
        "name": "save_exercise_plan",
        "description": (
            "Save a structured monthly exercise plan for one person. "
            "Call this after searching for exercises and assembling the full plan. "
            "Build separate plans for Chris and Kaitlyn — call this once per person."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "person_name": {
                    "type": "string",
                    "description": "First name of the person this plan is for",
                },
                "workout_days": {
                    "type": "array",
                    "description": "List of training days in the weekly schedule",
                    "items": {
                        "type": "object",
                        "properties": {
                            "day": {"type": "string", "description": "Day of the week, e.g. Monday"},
                            "focus": {"type": "string", "description": "Session focus, e.g. Upper Body Push"},
                            "exercises": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "exercise_id": {"type": "string"},
                                        "exercise_name": {"type": "string"},
                                        "sets": {"type": "integer"},
                                        "reps": {"type": "string"},
                                        "rest_seconds": {"type": "integer"},
                                    },
                                    "required": ["exercise_id", "exercise_name", "sets", "reps", "rest_seconds"],
                                },
                            },
                        },
                        "required": ["day", "focus", "exercises"],
                    },
                },
                "rest_days": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Days with no training, e.g. ['Wednesday', 'Sunday']",
                },
                "notes": {
                    "type": "string",
                    "description": "Any coaching notes, progressions, or context for the plan",
                },
            },
            "required": ["person_name", "workout_days"],
        },
    },
    {
        "name": "get_exercise_plan",
        "description": "Retrieve the saved monthly exercise plan for a person.",
        "input_schema": {
            "type": "object",
            "properties": {
                "person_name": {
                    "type": "string",
                    "description": "First name of the person whose plan to retrieve",
                },
            },
            "required": ["person_name"],
        },
    },
    {
        "name": "search_exercises",
        "description": (
            "Look up exercises from the ExerciseDB canonical database. "
            "Always use this before recommending specific exercises — it ensures consistent naming, "
            "accurate muscle targeting, and correct equipment. "
            "Returns exercise name, target muscle, equipment, secondary muscles, and form instructions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Search by exercise name, e.g. 'bench press', 'squat', 'deadlift'",
                },
                "body_part": {
                    "type": "string",
                    "description": "Filter by body part: back, cardio, chest, lower arms, lower legs, neck, shoulders, upper arms, upper legs, waist",
                },
                "target_muscle": {
                    "type": "string",
                    "description": "Filter by target muscle: abs, biceps, calves, delts, glutes, hamstrings, lats, pectorals, quads, traps, triceps, upper back",
                },
                "equipment": {
                    "type": "string",
                    "description": "Filter by equipment: barbell, body weight, cable, dumbbell, kettlebell, leverage machine, resistance band",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of results to return (default 8, max 15)",
                },
            },
        },
    },
]


def run_tool(name: str, inputs: dict) -> str:
    if name == "search_meals":
        filters = {}
        if "max_calories" in inputs:
            filters["maxCalories"] = inputs["max_calories"]
        if "min_protein" in inputs:
            filters["minProtein"] = inputs["min_protein"]

        meals = search_recipes(
            query=inputs.get("query", ""),
            number=inputs.get("number", 5),
            **filters,
        )

        if not meals:
            return "No recipes found for that search."

        lines = []
        for meal in meals:
            lines.append(
                f"- {meal.name} | {meal.calories_per_serving} kcal | "
                f"{meal.protein_g}g protein | {meal.carbs_g}g carbs | {meal.fat_g}g fat"
            )
        return "\n".join(lines)

    if name == "search_exercises":
        exercises = search_exercises(
            name=inputs.get("name", ""),
            body_part=inputs.get("body_part", ""),
            target_muscle=inputs.get("target_muscle", ""),
            equipment=inputs.get("equipment", ""),
            limit=inputs.get("limit", 8),
        )

        if not exercises:
            return "No exercises found for that search."

        lines = []
        for ex in exercises:
            secondary = ", ".join(ex.secondary_muscles) if ex.secondary_muscles else "none"
            instructions = " | ".join(ex.instructions[:3])
            lines.append(
                f"- {ex.name} | Target: {ex.target_muscle} | Equipment: {ex.equipment} "
                f"| Also works: {secondary}\n  Form: {instructions}"
            )
        return "\n".join(lines)

    if name == "save_exercise_plan":
        person_name = inputs["person_name"]
        plan = MonthlyPlan(
            person_name=person_name,
            created_date=str(date.today()),
            workout_days=[WorkoutDay(**d) for d in inputs["workout_days"]],
            rest_days=inputs.get("rest_days", []),
            notes=inputs.get("notes", ""),
        )
        filename = f"exercise_plan_{person_name.lower()}.json"
        with open(filename, "w") as f:
            json.dump(plan.model_dump(), f, indent=2)
        return (
            f"Exercise plan for {person_name} saved ({len(plan.workout_days)} training days/week). "
            f"File: {filename}"
        )

    if name == "get_exercise_plan":
        person_name = inputs["person_name"]
        filename = f"exercise_plan_{person_name.lower()}.json"
        try:
            with open(filename) as f:
                plan = MonthlyPlan(**json.load(f))
        except FileNotFoundError:
            return f"No exercise plan found for {person_name}. Build one first."

        lines = [f"Exercise plan for {plan.person_name} (created {plan.created_date}):"]
        for day in plan.workout_days:
            lines.append(f"\n{day.day} — {day.focus}")
            for ex in day.exercises:
                lines.append(f"  - {ex.exercise_name}: {ex.sets} sets × {ex.reps} (rest {ex.rest_seconds}s)")
        if plan.rest_days:
            lines.append(f"\nRest days: {', '.join(plan.rest_days)}")
        if plan.notes:
            lines.append(f"\nNotes: {plan.notes}")
        return "\n".join(lines)

    return f"Unknown tool: {name}"


def chat(user_message):
    conversation_history.append({"role": "user", "content": user_message})
    print(f"[DEBUG] History length: {len(conversation_history)} messages")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=conversation_history,
        )
    except anthropic.AuthenticationError:
        print("Your API key is invalid. Check your .env file.")
        return None
    except anthropic.RateLimitError:
        print("Too many requests. Wait a moment and try again.")
        return None
    except Exception as e:
        print(f"Something went wrong: {e}")
        return None

    # Tool use loop — Claude may call tools multiple times before giving a final answer
    while response.stop_reason == "tool_use":
        tool_uses = [b for b in response.content if b.type == "tool_use"]

        conversation_history.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tool_use in tool_uses:
            print(f"[DEBUG] Tool call: {tool_use.name}({tool_use.input})")
            result = run_tool(tool_use.name, tool_use.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result,
            })

        conversation_history.append({"role": "user", "content": tool_results})

        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=conversation_history,
            )
        except Exception as e:
            print(f"Something went wrong: {e}")
            return None

    assistant_message = next(b.text for b in response.content if hasattr(b, "text"))
    conversation_history.append({"role": "assistant", "content": assistant_message})
    return assistant_message


def main():
    print("Franky Fitness Agent")
    print("Type 'bye' to exit.\n")

    while True:
        user_input = input("You: ")

        if user_input.lower() == "bye":
            print("See you next time!")
            break

        response = chat(user_input)
        print(f"\nFRANKY: {response}\n")


if __name__ == "__main__":
    main()
