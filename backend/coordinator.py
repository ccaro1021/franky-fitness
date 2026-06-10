import time

from anthropic import Anthropic
from dotenv import load_dotenv

from backend.exercise_agent import run_exercise_agent
from backend.meal_agent import run_meal_agent

load_dotenv()

client = Anthropic()

ROUTER_SYSTEM_PROMPT = """You are a routing layer for Franky, a fitness and nutrition assistant. \
Decide which specialist should handle the user's latest message:

- "meal": meal planning, recipes, nutrition, macros, dietary preferences, grocery lists, food substitutions.
- "exercise": workout plans, exercises, training splits, sets/reps, equipment, fitness routines, injury-aware programming.

If the message is ambiguous, general, or a greeting/thanks, choose "meal" as the default.

Call the route tool with your decision."""

ROUTER_TOOLS = [
    {
        "name": "route",
        "description": "Choose which specialist should handle this message.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent": {
                    "type": "string",
                    "enum": ["meal", "exercise"],
                    "description": "The specialist that should handle this message",
                },
            },
            "required": ["agent"],
        },
    },
]


def _route(messages: list[dict]) -> tuple[str, dict]:
    """Classify the latest user message as 'meal' or 'exercise'. Falls back to 'meal' on error."""
    last_user_message = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"),
        "",
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=ROUTER_SYSTEM_PROMPT,
            tools=ROUTER_TOOLS,
            tool_choice={"type": "tool", "name": "route"},
            messages=[{"role": "user", "content": last_user_message}],
        )
    except Exception:
        return "meal", {"input_tokens": 0, "output_tokens": 0}

    tool_use = next(b for b in response.content if b.type == "tool_use")
    agent = tool_use.input.get("agent", "meal")
    usage = {"input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
    return agent, usage


def run_coordinator(
    messages: list[dict],
    profile: dict,
    current_meal_plan: dict | None = None,
    current_workout_plan: dict | None = None,
    preference_summary: dict | None = None,
) -> dict:
    """
    Classify the latest message and dispatch to the meal or exercise specialist.

    Returns:
        message, meal_plan, recipe, workout_plan, agent_runs (list of per-call usage/latency for logging)
    """
    start = time.time()
    agent, route_usage = _route(messages)
    routing_latency_ms = round((time.time() - start) * 1000)

    if agent == "exercise":
        result = run_exercise_agent(
            messages, profile, current_plan=current_workout_plan, preference_summary=preference_summary
        )
        result["meal_plan"] = None
        result["recipe"] = None
    else:
        result = run_meal_agent(
            messages, profile, current_plan=current_meal_plan, preference_summary=preference_summary
        )
        result["workout_plan"] = None

    result["agent_runs"] = [
        {
            "agent_type": "coordinator",
            "input_tokens": route_usage["input_tokens"],
            "output_tokens": route_usage["output_tokens"],
            "latency_ms": routing_latency_ms,
        },
        {
            "agent_type": f"{agent}_agent",
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
            "latency_ms": result["latency_ms"],
        },
    ]

    return result
