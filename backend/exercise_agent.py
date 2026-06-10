import time

from anthropic import Anthropic
from dotenv import load_dotenv

from exercisedb import search_exercises

load_dotenv()

client = Anthropic()

_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

TOOLS = [
    {
        "name": "search_exercises",
        "description": (
            "Search ExerciseDB for real exercises. Use this to find exercises for a workout day "
            "before including them in a plan. Returns exercise names, IDs, target muscles, "
            "equipment, and secondary muscles worked."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Exercise name to search for, e.g. 'bench press'",
                },
                "body_part": {
                    "type": "string",
                    "enum": [
                        "back", "cardio", "chest", "lower arms", "lower legs",
                        "neck", "shoulders", "upper arms", "upper legs", "waist",
                    ],
                    "description": "Body part to search by",
                },
                "target_muscle": {
                    "type": "string",
                    "description": "Target muscle to search by, e.g. 'quads', 'lats', 'biceps'",
                },
                "equipment": {
                    "type": "string",
                    "description": "Equipment to search by, e.g. 'barbell', 'dumbbell', 'body weight'",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of results to return (1-15, default 8)",
                },
            },
        },
    },
    {
        "name": "finalize_workout_plan",
        "description": (
            "Call this once you have assembled the complete workout plan for the week. "
            "Include every training day before calling this. Use exercise IDs and names "
            "from your search_exercises results, not invented exercises."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "workout_days": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "day": {"type": "string", "description": "Day of the week, e.g. Monday"},
                            "focus": {"type": "string", "description": "e.g. 'Upper Body Push', 'Legs'"},
                            "exercises": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "exercise_id": {"type": "string"},
                                        "exercise_name": {"type": "string"},
                                        "sets": {"type": "integer"},
                                        "reps": {"type": "string", "description": "e.g. '8-12', '30 seconds', 'to failure'"},
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
                    "description": "Days of the week with no training, e.g. ['Saturday', 'Sunday']",
                },
                "notes": {
                    "type": "string",
                    "description": "Coaching notes, progression tips, or form reminders for the week",
                },
            },
            "required": ["workout_days"],
        },
    },
]


def _format_plan_for_prompt(plan: dict) -> str:
    by_day = {d["day"]: d for d in plan.get("workout_days", [])}

    lines = []
    for day in _DAYS:
        if day not in by_day:
            continue
        day_entry = by_day[day]
        lines.append(f"{day} — {day_entry['focus']}")
        for ex in day_entry.get("exercises", []):
            lines.append(
                f"  {ex['exercise_name']}: {ex['sets']} sets x {ex['reps']} (rest {ex['rest_seconds']}s)"
            )

    if plan.get("rest_days"):
        lines.append("Rest days: " + ", ".join(plan["rest_days"]))
    if plan.get("notes"):
        lines.append(f"Notes: {plan['notes']}")

    return "\n".join(lines)


def _build_system_prompt(profile: dict, current_plan: dict | None = None) -> str:
    goals = ", ".join(profile["fitness_goals"])
    notes = profile.get("notes", "")

    prompt = f"""You are Franky, a personal training assistant for {profile['name']}.

{profile['name']}'s profile:
- Fitness goals: {goals}
{f"- Notes: {notes}" if notes else ""}

When building a workout plan:
1. Ask for available training days per week, equipment access, and any injuries or limitations — one focused question at a time.
2. Choose an appropriate training split (e.g. Upper/Lower, Push/Pull/Legs, Full Body) based on available days and goals.
3. Use search_exercises to find real exercises for each session — never invent exercise names or IDs.
4. Assign sets, reps, and rest periods appropriate to the goal (fat loss = higher reps/shorter rest, muscle building = moderate reps/longer rest).
5. Once the full plan is assembled, call finalize_workout_plan with structured data, then summarize it conversationally.

You are a coach, not a doctor. For injuries or medical concerns, recommend consulting a healthcare professional and avoid exercises that could aggravate a stated limitation."""

    if current_plan:
        plan_text = _format_plan_for_prompt(current_plan)
        prompt += f"""

{profile['name']}'s current saved workout plan:
{plan_text}

If {profile['name']} asks to adjust the plan, modify this one rather than starting over."""
    else:
        prompt += f"\n\n{profile['name']} has no saved workout plan yet."

    return prompt


def _run_tool(name: str, inputs: dict) -> tuple[str, dict | None]:
    """Returns (text_for_agent, structured_data_for_frontend)."""
    if name == "search_exercises":
        try:
            exercises = search_exercises(
                name=inputs.get("name", ""),
                body_part=inputs.get("body_part", ""),
                target_muscle=inputs.get("target_muscle", ""),
                equipment=inputs.get("equipment", ""),
                limit=inputs.get("limit", 8),
            )
        except Exception as e:
            return f"Exercise search is temporarily unavailable: {e}", None

        if not exercises:
            return "No exercises found for that search.", None

        lines = []
        for ex in exercises:
            secondary = ", ".join(ex.secondary_muscles) if ex.secondary_muscles else "none"
            lines.append(
                f"- {ex.name} (ID: {ex.id}) | Target: {ex.target_muscle} | "
                f"Equipment: {ex.equipment} | Also works: {secondary}"
            )
        return "\n".join(lines), None

    if name == "finalize_workout_plan":
        return "Workout plan finalized.", inputs

    return f"Unknown tool: {name}", None


def run_exercise_agent(
    messages: list[dict],
    profile: dict,
    current_plan: dict | None = None,
) -> dict:
    """
    Run the exercise planning agent for one conversation turn.

    Args:
        messages: Full conversation history (role/content pairs from the frontend)
        profile: User profile from profiles.py
        current_plan: Most recently saved workout plan for this person, injected as context

    Returns:
        message, workout_plan, input_tokens, output_tokens, latency_ms
    """
    start = time.time()
    input_tokens = 0
    output_tokens = 0
    workout_plan: dict | None = None

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

            if tool_use.name == "finalize_workout_plan":
                workout_plan = result_data

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
        "workout_plan": workout_plan,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": latency_ms,
    }
