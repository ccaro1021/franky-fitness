import json
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.auth import (
    create_session,
    delete_session,
    get_current_user,
    hash_password,
    verify_password,
)
from backend.coordinator import run_coordinator
from backend.database import get_connection, setup_tables
from backend.grocery_agent import normalize_ingredients
from backend.preferences import EMPTY_SUMMARY, forget_item, get_preference_summary, record_feedback
from backend.transcripts import write_transcript
from backend.users import build_profile_context, create_user, get_profile, get_user_by_email, update_profile
from grocery import generate_grocery_list
from spoonacular import get_recipe

GROCERY_LIST_KEYWORDS = ["grocery list", "shopping list"]
SESSION_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_tables()
    yield


app = FastAPI(title="Franky Fitness API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]


class SavePlanRequest(BaseModel):
    plan: dict
    type: str = "meal_plan"


class FeedbackRequest(BaseModel):
    plan_id: int | None = None
    item_type: str
    item_name: str
    rating: str
    note: str | None = None


class ForgetPreferenceRequest(BaseModel):
    item_type: str
    item_name: str


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class ProfileUpdateRequest(BaseModel):
    height_inches: float | None = None
    weight_lbs: float | None = None
    target_weight_lbs: float | None = None
    dietary_restrictions: list[str] = []
    fitness_goals: list[str] = []
    notes: str = ""


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        "session_token",
        token,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )


@app.post("/api/auth/signup")
def signup(req: SignupRequest, response: Response):
    if get_user_by_email(req.email):
        raise HTTPException(status_code=409, detail="Email already registered")

    user = create_user(req.email, req.name, hash_password(req.password))
    token = create_session(user["id"])
    _set_session_cookie(response, token)
    return user


@app.post("/api/auth/login")
def login(req: LoginRequest, response: Response):
    user = get_user_by_email(req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_session(user["id"])
    _set_session_cookie(response, token)
    return {"id": user["id"], "email": user["email"], "name": user["name"]}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        delete_session(token)
    response.delete_cookie("session_token", path="/")
    return {"ok": True}


@app.get("/api/auth/me")
def me(user: dict = Depends(get_current_user)):
    return user


@app.get("/api/profile")
def get_my_profile(user: dict = Depends(get_current_user)):
    return get_profile(user["id"])


@app.put("/api/profile")
def put_my_profile(req: ProfileUpdateRequest, user: dict = Depends(get_current_user)):
    return update_profile(
        user["id"],
        req.height_inches,
        req.weight_lbs,
        req.target_weight_lbs,
        req.dietary_restrictions,
        req.fitness_goals,
        req.notes,
    )


@app.get("/api/preferences")
def get_my_preferences(user: dict = Depends(get_current_user)):
    return get_preference_summary(user["id"]) or EMPTY_SUMMARY


@app.post("/api/preferences/forget")
def forget_my_preference(req: ForgetPreferenceRequest, user: dict = Depends(get_current_user)):
    return forget_item(user["id"], req.item_type, req.item_name)


def _prepare_grocery_data(plan_id: int, plan: dict) -> tuple[dict, dict | None]:
    """Fetch missing ingredients and normalize their names for a saved meal plan.

    For each meal without `ingredients_fetched`, fetches the full recipe from
    Spoonacular (a failed fetch leaves that meal pending for the next request).
    Any ingredient without a `canonical_name` is normalized in one batch via
    grocery_agent.normalize_ingredients. Persists changes back onto plans.content
    so repeat requests are pure code. Returns (plan, normalizer transcript or None).
    """
    changed = False
    for meal in plan.get("meals", []):
        if meal.get("ingredients_fetched"):
            continue
        if meal.get("ingredients"):
            # Plan saved before this slice already has ingredients — nothing to fetch.
            meal["ingredients_fetched"] = True
            changed = True
            continue
        spoonacular_id = meal.get("spoonacular_id")
        if not spoonacular_id:
            meal["ingredients"] = []
            meal["ingredients_fetched"] = True
            changed = True
            continue
        try:
            recipe = get_recipe(spoonacular_id)
            meal["ingredients"] = [ing.model_dump() for ing in recipe.ingredients]
            meal["ingredients_fetched"] = True
            changed = True
        except Exception:
            pass  # leave ingredients_fetched unset; retried on the next request

    raw_names = {
        ing["name"]
        for meal in plan.get("meals", [])
        for ing in meal.get("ingredients", [])
        if "canonical_name" not in ing
    }

    transcript = None
    if raw_names:
        mapping, transcript = normalize_ingredients(list(raw_names))
        for meal in plan.get("meals", []):
            for ing in meal.get("ingredients", []):
                if "canonical_name" not in ing:
                    ing["canonical_name"] = mapping.get(ing["name"].lower(), ing["name"].lower())
                    changed = True

    if changed:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE plans SET content = %s WHERE id = %s", (json.dumps(plan), plan_id))
            conn.commit()

    return plan, transcript


def _log_grocery_transcript(transcript: dict, user_id: int) -> None:
    """Write a grocery_normalizer transcript and its agent_runs row (only happens on cache misses)."""
    write_transcript(transcript)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO agent_runs
                   (agent_type, user_id, input_tokens, output_tokens, latency_ms, agent_invoked, transcript_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    transcript["agent_type"],
                    user_id,
                    transcript["usage"]["input_tokens"],
                    transcript["usage"]["output_tokens"],
                    transcript["latency_ms"],
                    transcript["agent_invoked"],
                    transcript["transcript_id"],
                ),
            )
        conn.commit()


@app.post("/api/chat")
def chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    # Inject the most recently saved plan of each type so specialists know this week's plans
    current_meal_plan = None
    current_meal_plan_id = None
    current_workout_plan = None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, content FROM plans
                   WHERE user_id = %s AND type = 'meal_plan'
                   ORDER BY created_at DESC LIMIT 1""",
                (user["id"],),
            )
            row = cur.fetchone()
            if row:
                current_meal_plan_id = row[0]
                current_meal_plan = row[1]

            cur.execute(
                """SELECT content FROM plans
                   WHERE user_id = %s AND type = 'workout_plan'
                   ORDER BY created_at DESC LIMIT 1""",
                (user["id"],),
            )
            row = cur.fetchone()
            if row:
                current_workout_plan = row[0]

    # Grocery lists are pure code, not an agent call — short-circuit if asked for one
    last_message = messages[-1]["content"].lower() if messages else ""
    if current_meal_plan and any(kw in last_message for kw in GROCERY_LIST_KEYWORDS):
        plan, transcript = _prepare_grocery_data(current_meal_plan_id, current_meal_plan)
        if transcript:
            _log_grocery_transcript(transcript, user["id"])

        items = generate_grocery_list(plan)
        missing = [m["name"] for m in plan.get("meals", []) if not m.get("ingredients_fetched")]
        message = "Here's your grocery list for this week's plan!"
        if missing:
            message += f" (Couldn't fetch ingredients for: {', '.join(missing)} — try again later.)"

        return {
            "message": message,
            "meal_plan": None,
            "recipe": None,
            "grocery_list": {"items": [item.model_dump() for item in items]},
            "workout_plan": None,
        }

    profile = build_profile_context(user["id"])
    preference_summary = get_preference_summary(user["id"])

    try:
        result = run_coordinator(
            messages,
            profile,
            current_meal_plan=current_meal_plan,
            current_workout_plan=current_workout_plan,
            preference_summary=preference_summary,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    with get_connection() as conn:
        with conn.cursor() as cur:
            for run in result["agent_runs"]:
                transcript = run["transcript"]
                write_transcript(transcript)
                cur.execute(
                    """INSERT INTO agent_runs
                       (agent_type, user_id, input_tokens, output_tokens, latency_ms, agent_invoked, transcript_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        run["agent_type"],
                        user["id"],
                        run["input_tokens"],
                        run["output_tokens"],
                        run["latency_ms"],
                        run["agent_invoked"],
                        transcript["transcript_id"],
                    ),
                )
        conn.commit()

    return {
        "message": result["message"],
        "meal_plan": result["meal_plan"],
        "recipe": result["recipe"],
        "grocery_list": None,
        "workout_plan": result["workout_plan"],
    }


@app.post("/api/plans")
def save_plan(req: SavePlanRequest, user: dict = Depends(get_current_user)):
    if req.type not in ("meal_plan", "workout_plan"):
        raise HTTPException(status_code=400, detail=f"Unknown plan type: {req.type}")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO plans (user_id, type, content) VALUES (%s, %s, %s) RETURNING id",
                (user["id"], req.type, json.dumps(req.plan)),
            )
            plan_id = cur.fetchone()[0]
        conn.commit()

    return {"id": plan_id}


@app.get("/api/plans")
def list_plans(type: str = "meal_plan", user: dict = Depends(get_current_user)):
    if type not in ("meal_plan", "workout_plan"):
        raise HTTPException(status_code=400, detail=f"Unknown plan type: {type}")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, content, created_at
                   FROM plans
                   WHERE user_id = %s AND type = %s
                   ORDER BY created_at DESC""",
                (user["id"], type),
            )
            rows = cur.fetchall()

    return [
        {
            "id": r[0],
            "content": r[1],
            "created_at": r[2].isoformat(),
        }
        for r in rows
    ]


@app.get("/api/plans/{plan_id}")
def get_plan(plan_id: int, user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, content, created_at FROM plans WHERE id = %s AND user_id = %s",
                (plan_id, user["id"]),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Plan not found")

    return {
        "id": row[0],
        "content": row[1],
        "created_at": row[2].isoformat(),
    }


@app.post("/api/feedback")
def submit_feedback(req: FeedbackRequest, user: dict = Depends(get_current_user)):
    if req.item_type not in ("meal", "exercise"):
        raise HTTPException(status_code=400, detail=f"Unknown item_type: {req.item_type}")

    if req.rating not in ("positive", "negative"):
        raise HTTPException(status_code=400, detail=f"Unknown rating: {req.rating}")

    summary = record_feedback(
        user["id"], req.plan_id, req.item_type, req.item_name, req.rating, req.note
    )
    return {"summary": summary}


@app.get("/api/plans/{plan_id}/grocery-list")
def get_grocery_list(plan_id: int, user: dict = Depends(get_current_user)):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT content FROM plans WHERE id = %s AND user_id = %s AND type = 'meal_plan'",
                (plan_id, user["id"]),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan, transcript = _prepare_grocery_data(plan_id, row[0])
    if transcript:
        _log_grocery_transcript(transcript, user["id"])

    items = generate_grocery_list(plan)
    missing = [m["name"] for m in plan.get("meals", []) if not m.get("ingredients_fetched")]
    return {"items": [item.model_dump() for item in items], "missing_meals": missing or None}
