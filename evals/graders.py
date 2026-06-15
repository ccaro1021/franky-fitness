"""Graders: each takes a Transcript and returns {assertion, passed, reasoning}.

Code-based graders read only transcript["outcome"] and transcript["agent_invoked"]
(never the tool-call path), so they stay valid if an agent's internal tool-use
sequence changes. The LLM-as-judge grader (`judge`) is for fuzzy checks that
can't be expressed as a simple assertion.
"""

import re

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

_client = Anthropic()
_JUDGE_MODEL = "claude-haiku-4-5-20251001"

_JUDGE_TOOLS = [
    {
        "name": "judgment",
        "description": "Record whether the agent's output satisfies the rubric.",
        "input_schema": {
            "type": "object",
            "properties": {
                "passed": {"type": "boolean"},
                "reasoning": {"type": "string", "description": "One or two sentences explaining the verdict"},
            },
            "required": ["passed", "reasoning"],
        },
    },
]

_RESTRICTION_KEYWORDS = {
    "vegetarian": [
        "chicken", "beef", "pork", "turkey", "bacon", "ham", "sausage", "steak",
        "fish", "salmon", "shrimp", "tuna", "anchovy", "lamb", "meat",
    ],
    "vegan": [
        "chicken", "beef", "pork", "turkey", "bacon", "ham", "sausage", "steak",
        "fish", "salmon", "shrimp", "tuna", "anchovy", "lamb", "meat",
        "egg", "milk", "cheese", "yogurt", "butter", "honey", "cream",
    ],
    "pescatarian": [
        "chicken", "beef", "pork", "turkey", "bacon", "ham", "sausage", "steak", "lamb", "meat",
    ],
}


def routed_to(expected: str):
    """Pass if the coordinator routed this turn to the expected specialist ('meal' or 'exercise')."""
    def grader(transcript: dict) -> dict:
        actual = transcript.get("agent_invoked")
        passed = actual == expected
        return {
            "assertion": f"routed_to({expected!r})",
            "passed": passed,
            "reasoning": f"agent_invoked={actual!r}",
        }
    return grader


def _plan_days(outcome: dict) -> set[str]:
    meal_plan = outcome.get("meal_plan")
    if meal_plan:
        return {meal["day"] for meal in meal_plan.get("meals", [])}
    workout_plan = outcome.get("workout_plan")
    if workout_plan:
        return {day["day"] for day in workout_plan.get("workout_days", [])}
    return set()


def plan_has_n_days(n: int):
    """Pass if the finalized plan (meal or workout) covers exactly n distinct days."""
    def grader(transcript: dict) -> dict:
        days = _plan_days(transcript["outcome"])
        if not days:
            return {"assertion": f"plan_has_n_days({n})", "passed": False, "reasoning": "no finalized plan in outcome"}
        passed = len(days) == n
        return {
            "assertion": f"plan_has_n_days({n})",
            "passed": passed,
            "reasoning": f"plan covers {len(days)} days: {sorted(days)}",
        }
    return grader


def every_meal_min_protein(grams: int, meal_types: list[str] | None = None):
    """Pass if every meal of the given meal_types (default: all) has at least `grams` of protein."""
    def grader(transcript: dict) -> dict:
        meal_plan = transcript["outcome"].get("meal_plan")
        if not meal_plan:
            return {"assertion": f"every_meal_min_protein({grams})", "passed": False, "reasoning": "no meal_plan in outcome"}
        meals = meal_plan.get("meals", [])
        if meal_types:
            meals = [m for m in meals if m.get("meal_type") in meal_types]
        low = [(m["name"], m["protein_g"]) for m in meals if m.get("protein_g", 0) < grams]
        passed = len(low) == 0
        return {
            "assertion": f"every_meal_min_protein({grams}, meal_types={meal_types})",
            "passed": passed,
            "reasoning": "all meals meet the protein minimum" if passed else f"below minimum: {low}",
        }
    return grader


def no_restricted_ingredients(restrictions: list[str]):
    """Pass if no meal name or ingredient in the finalized meal plan matches a restricted-food keyword."""
    keywords = set()
    for restriction in restrictions:
        keywords |= set(_RESTRICTION_KEYWORDS.get(restriction.lower(), []))

    def grader(transcript: dict) -> dict:
        meal_plan = transcript["outcome"].get("meal_plan")
        if not meal_plan:
            return {"assertion": f"no_restricted_ingredients({restrictions})", "passed": False, "reasoning": "no meal_plan in outcome"}

        violations = []
        for meal in meal_plan.get("meals", []):
            text = meal.get("name", "").lower()
            for ingredient in meal.get("ingredients", []):
                text += " " + ingredient.get("name", "").lower()
            for keyword in keywords:
                if keyword in text:
                    violations.append((meal.get("name"), keyword))

        passed = len(violations) == 0
        return {
            "assertion": f"no_restricted_ingredients({restrictions})",
            "passed": passed,
            "reasoning": "no restricted ingredients found" if passed else f"violations: {violations}",
        }
    return grader


def _equipment_by_exercise_id(transcript: dict) -> dict[str, str]:
    """Parse 'Equipment: X' from search_exercises tool results, keyed by exercise ID."""
    mapping = {}
    line_re = re.compile(r"\(ID:\s*(\S+)\)\s*\|\s*Target:.*?\|\s*Equipment:\s*([^|]+)\|")
    for step in transcript.get("steps", []):
        if step.get("name") != "search_exercises":
            continue
        for line in str(step.get("result") or "").splitlines():
            match = line_re.search(line)
            if match:
                mapping[match.group(1)] = match.group(2).strip().lower()
    return mapping


def equipment_subset(allowed: list[str]):
    """Pass if every exercise in the finalized workout plan uses only allowed equipment."""
    allowed_set = {a.lower() for a in allowed}

    def grader(transcript: dict) -> dict:
        workout_plan = transcript["outcome"].get("workout_plan")
        if not workout_plan:
            return {"assertion": f"equipment_subset({allowed})", "passed": False, "reasoning": "no workout_plan in outcome"}

        equipment_by_id = _equipment_by_exercise_id(transcript)
        violations = []
        for day in workout_plan.get("workout_days", []):
            for exercise in day.get("exercises", []):
                equipment = equipment_by_id.get(exercise.get("exercise_id"))
                if equipment is not None and equipment not in allowed_set:
                    violations.append((exercise.get("exercise_name"), equipment))

        passed = len(violations) == 0
        return {
            "assertion": f"equipment_subset({allowed})",
            "passed": passed,
            "reasoning": "all exercises use allowed equipment" if passed else f"violations: {violations}",
        }
    return grader


def emitted_no_plan():
    """Pass if the agent did NOT finalize a meal or workout plan this turn."""
    def grader(transcript: dict) -> dict:
        outcome = transcript["outcome"]
        has_plan = bool(outcome.get("meal_plan") or outcome.get("workout_plan"))
        return {
            "assertion": "emitted_no_plan()",
            "passed": not has_plan,
            "reasoning": "a plan was emitted" if has_plan else "no plan emitted",
        }
    return grader


def macros_trace_to_search():
    """Pass if every macro number cited in the agent's reply also appears in a search_meals result."""
    def grader(transcript: dict) -> dict:
        output = transcript.get("output", "")
        search_text = "\n".join(
            str(step.get("result") or "") for step in transcript.get("steps", []) if step.get("name") == "search_meals"
        )

        cited = set(re.findall(r"\b(\d+)\s*(?:kcal|g\s*(?:protein|carbs|fat))\b", output, flags=re.IGNORECASE))
        if not cited:
            return {"assertion": "macros_trace_to_search()", "passed": True, "reasoning": "no macros cited in output"}

        untraced = sorted(n for n in cited if n not in search_text)
        passed = len(untraced) == 0
        return {
            "assertion": "macros_trace_to_search()",
            "passed": passed,
            "reasoning": "all cited macros trace to search_meals results" if passed else f"untraced numbers: {untraced}",
        }
    return grader


def called_tool_with(tool_name: str, expected_fields: dict):
    """Pass if a tool_use step named `tool_name` was called with input containing
    every key/value in `expected_fields` (list values compared case-insensitively
    as sets of strings)."""
    def grader(transcript: dict) -> dict:
        calls = [step["input"] for step in transcript.get("steps", []) if step.get("name") == tool_name]
        if not calls:
            return {
                "assertion": f"called_tool_with({tool_name!r}, {expected_fields!r})",
                "passed": False,
                "reasoning": f"no {tool_name} tool call found",
            }

        for call in calls:
            mismatches = []
            for key, expected_value in expected_fields.items():
                actual_value = call.get(key)
                if isinstance(expected_value, list):
                    if {str(v).lower() for v in (actual_value or [])} != {str(v).lower() for v in expected_value}:
                        mismatches.append((key, actual_value, expected_value))
                elif actual_value != expected_value:
                    mismatches.append((key, actual_value, expected_value))

            if not mismatches:
                return {
                    "assertion": f"called_tool_with({tool_name!r}, {expected_fields!r})",
                    "passed": True,
                    "reasoning": f"matched call: {call}",
                }

        return {
            "assertion": f"called_tool_with({tool_name!r}, {expected_fields!r})",
            "passed": False,
            "reasoning": f"no matching call; calls were: {calls}",
        }
    return grader


def judge(rubric: str):
    """LLM-as-judge: pass if Claude agrees the agent's output satisfies the rubric."""
    def grader(transcript: dict) -> dict:
        prompt = (
            f"Rubric: {rubric}\n\n"
            f"Agent's output:\n{transcript.get('output', '')}\n\n"
            "Does the agent's output satisfy the rubric? Call the judgment tool with your verdict."
        )
        try:
            response = _client.messages.create(
                model=_JUDGE_MODEL,
                max_tokens=300,
                tools=_JUDGE_TOOLS,
                tool_choice={"type": "tool", "name": "judgment"},
                messages=[{"role": "user", "content": prompt}],
            )
            tool_use = next(b for b in response.content if b.type == "tool_use")
            passed = bool(tool_use.input.get("passed", False))
            reasoning = tool_use.input.get("reasoning", "")
        except Exception as e:
            return {"assertion": f"judge({rubric!r})", "passed": False, "reasoning": f"judge call failed: {e}"}

        return {"assertion": f"judge({rubric!r})", "passed": passed, "reasoning": reasoning}
    return grader
