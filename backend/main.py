import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.coordinator import run_coordinator
from backend.database import get_connection, setup_tables
from backend.profiles import PEOPLE, PROFILES
from grocery import generate_grocery_list

GROCERY_LIST_KEYWORDS = ["grocery list", "shopping list"]


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
)


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[Message]
    person: str


class SavePlanRequest(BaseModel):
    person: str
    plan: dict
    type: str = "meal_plan"


@app.get("/api/people")
def list_people():
    return PEOPLE


@app.post("/api/chat")
def chat(req: ChatRequest):
    if req.person not in PROFILES:
        raise HTTPException(status_code=400, detail=f"Unknown person: {req.person}")

    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    # Inject the most recently saved plan of each type so specialists know this week's plans
    current_meal_plan = None
    current_workout_plan = None
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT content FROM plans
                   WHERE person_name = %s AND type = 'meal_plan'
                   ORDER BY created_at DESC LIMIT 1""",
                (req.person,),
            )
            row = cur.fetchone()
            if row:
                current_meal_plan = row[0]

            cur.execute(
                """SELECT content FROM plans
                   WHERE person_name = %s AND type = 'workout_plan'
                   ORDER BY created_at DESC LIMIT 1""",
                (req.person,),
            )
            row = cur.fetchone()
            if row:
                current_workout_plan = row[0]

    # Grocery lists are pure code, not an agent call — short-circuit if asked for one
    last_message = messages[-1]["content"].lower() if messages else ""
    if current_meal_plan and any(kw in last_message for kw in GROCERY_LIST_KEYWORDS):
        items = generate_grocery_list(current_meal_plan)
        return {
            "message": "Here's your grocery list for this week's plan!",
            "meal_plan": None,
            "recipe": None,
            "grocery_list": {"items": [item.model_dump() for item in items]},
            "workout_plan": None,
        }

    try:
        result = run_coordinator(
            messages,
            PROFILES[req.person],
            current_meal_plan=current_meal_plan,
            current_workout_plan=current_workout_plan,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    with get_connection() as conn:
        with conn.cursor() as cur:
            for run in result["agent_runs"]:
                cur.execute(
                    """INSERT INTO agent_runs (agent_type, person_name, input_tokens, output_tokens, latency_ms)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (run["agent_type"], req.person, run["input_tokens"], run["output_tokens"], run["latency_ms"]),
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
def save_plan(req: SavePlanRequest):
    if req.person not in PROFILES:
        raise HTTPException(status_code=400, detail=f"Unknown person: {req.person}")

    if req.type not in ("meal_plan", "workout_plan"):
        raise HTTPException(status_code=400, detail=f"Unknown plan type: {req.type}")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO plans (person_name, type, content) VALUES (%s, %s, %s) RETURNING id",
                (req.person, req.type, json.dumps(req.plan)),
            )
            plan_id = cur.fetchone()[0]
        conn.commit()

    return {"id": plan_id}


@app.get("/api/plans")
def list_plans(person: str, type: str = "meal_plan"):
    if person not in PROFILES:
        raise HTTPException(status_code=400, detail=f"Unknown person: {person}")

    if type not in ("meal_plan", "workout_plan"):
        raise HTTPException(status_code=400, detail=f"Unknown plan type: {type}")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, person_name, content, created_at
                   FROM plans
                   WHERE person_name = %s AND type = %s
                   ORDER BY created_at DESC""",
                (person, type),
            )
            rows = cur.fetchall()

    return [
        {
            "id": r[0],
            "person_name": r[1],
            "content": r[2],
            "created_at": r[3].isoformat(),
        }
        for r in rows
    ]


@app.get("/api/plans/{plan_id}")
def get_plan(plan_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, person_name, content, created_at FROM plans WHERE id = %s",
                (plan_id,),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Plan not found")

    return {
        "id": row[0],
        "person_name": row[1],
        "content": row[2],
        "created_at": row[3].isoformat(),
    }


@app.get("/api/plans/{plan_id}/grocery-list")
def get_grocery_list(plan_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT content FROM plans WHERE id = %s AND type = 'meal_plan'",
                (plan_id,),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Plan not found")

    items = generate_grocery_list(row[0])
    return {"items": [item.model_dump() for item in items]}
