import time

from anthropic import Anthropic
from dotenv import load_dotenv

from exercisedb import search_exercises

from backend.transcripts import build_transcript
from backend.users import patch_profile

load_dotenv()

client = Anthropic()

MODEL = "claude-sonnet-4-6"
MAX_TURNS = 10  # cap on tool-use round-trips before bailing out with a fallback message

_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

TOOLS = [
    {
        "name": "search_exercises",
        "description": (
            "Search ExerciseDB for real exercises. Call this once per exercise slot you "
            "need to fill before finalizing a plan. Combine filters to narrow results: "
            "equipment constrains by available gear (e.g. equipment='dumbbell' for a "
            "dumbbell-only program), body_part/target_muscle narrow by muscle group "
            "(e.g. body_part='chest', target_muscle='triceps'), and name searches by "
            "exercise name (e.g. name='bench press') when the user requests a specific "
            "movement. Returns exercise names, IDs, target muscles, equipment, and "
            "secondary muscles — use the returned id and name directly in "
            "finalize_workout_plan, never invent your own."
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
            "Call this exactly once you have assembled the complete workout plan for "
            "the week — one entry per training day, plus rest_days for the rest. "
            "exercise_id and exercise_name must come from a search_exercises result "
            "for that exercise; never invent exercises or IDs. If the user specified "
            "available equipment, every exercise's equipment (visible in "
            "search_exercises results) must be within that constraint."
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
    {
        "name": "update_profile",
        "description": (
            "Save durable personal info the user shares in chat (height, weight, target "
            "weight, dietary restrictions, fitness goals, general notes like injuries) "
            "to their profile, so future plans use it automatically. Only call this for "
            "info meant to persist — not for one-off, single-session preferences (e.g. "
            "'let's skip legs today'). Only include the fields the user actually stated; "
            "omit everything else."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "height_inches": {
                    "type": "number",
                    "description": "Total height in inches (e.g. 5'10\" = 70). Overwrites any existing value.",
                },
                "weight_lbs": {
                    "type": "number",
                    "description": "Current weight in pounds. Overwrites any existing value.",
                },
                "target_weight_lbs": {
                    "type": "number",
                    "description": "Target/goal weight in pounds. Overwrites any existing value.",
                },
                "add_dietary_restrictions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New dietary restrictions to add (e.g. ['shellfish allergy']). Merged with existing, case-insensitive de-duped.",
                },
                "add_fitness_goals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New fitness goals to add (e.g. ['train for a 10k']). Merged with existing, case-insensitive de-duped.",
                },
                "append_notes": {
                    "type": "string",
                    "description": "A general note to remember (e.g. 'Has a bad knee, go easy on lunges'). Appended to existing notes on a new line.",
                },
            },
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


def _format_preferences_for_prompt(preference_summary: dict) -> str:
    lines = []
    if preference_summary.get("liked_workouts"):
        lines.append(
            "- Liked exercises (include more like these): " + ", ".join(preference_summary["liked_workouts"])
        )
    if preference_summary.get("disliked_workouts"):
        lines.append(
            "- Disliked exercises (avoid these and very similar movements): "
            + ", ".join(preference_summary["disliked_workouts"])
        )
    return "\n".join(lines)


def _format_stats_for_prompt(profile: dict) -> str:
    lines = []
    if profile.get("height_inches"):
        lines.append(f"- Height: {profile['height_inches']} in")
    if profile.get("weight_lbs"):
        lines.append(f"- Current weight: {profile['weight_lbs']} lbs")
    if profile.get("target_weight_lbs"):
        lines.append(f"- Target weight: {profile['target_weight_lbs']} lbs")
    if profile.get("bmi"):
        lines.append(f"- BMI: {profile['bmi']} (context only — not a diagnosis)")
    return "\n".join(lines) + "\n" if lines else ""


def _profile_incomplete(profile: dict) -> bool:
    """True if fitness_goals is empty."""
    return not profile.get("fitness_goals")


def _build_system_prompt(
    profile: dict, current_plan: dict | None = None, preference_summary: dict | None = None
) -> str:
    goals = ", ".join(profile["fitness_goals"])
    notes = profile.get("notes", "")

    prompt = f"""You are Franky, a personal training assistant for {profile['name']}.

{profile['name']}'s profile:
- Fitness goals: {goals}
{f"- Notes: {notes}" if notes else ""}
{_format_stats_for_prompt(profile)}
When building a workout plan:
1. Ask for available training days per week, equipment access, and any injuries or limitations — one focused question at a time.
2. Choose an appropriate training split (e.g. Upper/Lower, Push/Pull/Legs, Full Body) based on available days and goals.
3. Before each search_exercises call, state in one short sentence what you're about to look for and why (e.g. "Searching for a dumbbell chest exercise for Monday's push day").
4. Use search_exercises to find real exercises for each session — never invent exercise names or IDs.
5. Assign sets, reps, and rest periods appropriate to the goal (fat loss = higher reps/shorter rest, muscle building = moderate reps/longer rest).
6. Once the full plan is assembled, call finalize_workout_plan with structured data, then summarize it conversationally.

If {profile['name']} states durable personal info meant to persist — height, weight, target weight, a new dietary restriction, a new fitness goal, or a general note like an injury — call update_profile to save it, and confirm in plain language what you saved (don't restate the whole profile). Don't call it for one-off, single-session preferences (e.g. "let's skip legs today").
{"\nWhen you call finalize_workout_plan, also include one short sentence in your reply noting that sharing fitness goals (via chat or the Profile page) would help tailor the program further." if _profile_incomplete(profile) else ""}
You are a coach, not a doctor. For injuries or medical concerns, recommend consulting a healthcare professional and avoid exercises that could aggravate a stated limitation."""

    if current_plan:
        plan_text = _format_plan_for_prompt(current_plan)
        prompt += f"""

{profile['name']}'s current saved workout plan:
{plan_text}

If {profile['name']} asks to adjust the plan, modify this one rather than starting over."""
    else:
        prompt += f"\n\n{profile['name']} has no saved workout plan yet."

    if preference_summary:
        preferences_text = _format_preferences_for_prompt(preference_summary)
        if preferences_text:
            prompt += f"\n\nKnown preferences for {profile['name']} (from past feedback):\n{preferences_text}"

    return prompt


def _describe_profile_update(inputs: dict) -> str:
    """Describe an update_profile call's inputs in plain language, for the tool_result."""
    parts = []
    if "height_inches" in inputs:
        parts.append(f"height to {inputs['height_inches']} in")
    if "weight_lbs" in inputs:
        parts.append(f"weight to {inputs['weight_lbs']} lbs")
    if "target_weight_lbs" in inputs:
        parts.append(f"target weight to {inputs['target_weight_lbs']} lbs")
    if inputs.get("add_dietary_restrictions"):
        parts.append("added " + ", ".join(f"'{item}'" for item in inputs["add_dietary_restrictions"]) + " to dietary restrictions")
    if inputs.get("add_fitness_goals"):
        parts.append("added " + ", ".join(f"'{item}'" for item in inputs["add_fitness_goals"]) + " to fitness goals")
    if inputs.get("append_notes"):
        parts.append(f"added a note: '{inputs['append_notes']}'")

    if not parts:
        return "No profile fields provided."
    return "Noted: " + "; ".join(parts) + "."


def _run_tool(name: str, inputs: dict, user_id: int | None = None) -> tuple[str, dict | None]:
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

    if name == "update_profile":
        if user_id is not None:
            patch_profile(user_id, **inputs)
        return _describe_profile_update(inputs), None

    return f"Unknown tool: {name}", None


def run_exercise_agent(
    messages: list[dict],
    profile: dict,
    current_plan: dict | None = None,
    preference_summary: dict | None = None,
    user_id: int | None = None,
) -> dict:
    """
    Run the exercise planning agent for one conversation turn.

    Args:
        messages: Full conversation history (role/content pairs from the frontend)
        profile: User profile from profiles.py
        current_plan: Most recently saved workout plan for this person, injected as context
        preference_summary: Liked/disliked exercises derived from past feedback, injected as context
        user_id: Current user's id, for update_profile to persist against; None in the eval harness

    Returns:
        message, workout_plan, input_tokens, output_tokens, latency_ms
    """
    start = time.time()
    input_tokens = 0
    output_tokens = 0
    workout_plan: dict | None = None

    system = _build_system_prompt(profile, current_plan, preference_summary)
    history = list(messages)

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            messages=history,
        )
    except Exception as e:
        raise RuntimeError(f"Agent call failed: {e}") from e

    input_tokens += response.usage.input_tokens
    output_tokens += response.usage.output_tokens

    turns = 1
    hit_max_turns = False

    while response.stop_reason == "tool_use":
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        history.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tool_use in tool_uses:
            result_text, result_data = _run_tool(tool_use.name, tool_use.input, user_id)

            if tool_use.name == "finalize_workout_plan":
                workout_plan = result_data

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_use.id,
                "content": result_text,
            })

        history.append({"role": "user", "content": tool_results})

        if turns >= MAX_TURNS:
            hit_max_turns = True
            break

        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=system,
                tools=TOOLS,
                messages=history,
            )
        except Exception as e:
            raise RuntimeError(f"Agent call failed: {e}") from e

        input_tokens += response.usage.input_tokens
        output_tokens += response.usage.output_tokens
        turns += 1

    if hit_max_turns:
        message = (
            "I'm having trouble wrapping this up after a lot of back-and-forth. "
            "Could you try rephrasing your request or breaking it into smaller asks?"
        )
        final_history = history
    else:
        message = next(b.text for b in response.content if hasattr(b, "text"))
        final_history = history + [{"role": "assistant", "content": response.content}]

    latency_ms = round((time.time() - start) * 1000)

    transcript = build_transcript(
        agent_type="exercise_agent",
        model=MODEL,
        system=system,
        inputs=messages,
        history=final_history,
        output=message,
        outcome={"workout_plan": workout_plan, "hit_max_turns": hit_max_turns},
        usage={"input_tokens": input_tokens, "output_tokens": output_tokens},
        latency_ms=latency_ms,
    )

    return {
        "message": message,
        "workout_plan": workout_plan,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": latency_ms,
        "transcript": transcript,
    }
