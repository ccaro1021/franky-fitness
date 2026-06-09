import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.database import get_connection, setup_tables
from backend.meal_agent import run_meal_agent
from backend.profiles import PEOPLE, PROFILES


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


@app.get("/api/people")
def list_people():
    return PEOPLE


@app.post("/api/chat")
def chat(req: ChatRequest):
    if req.person not in PROFILES:
        raise HTTPException(status_code=400, detail=f"Unknown person: {req.person}")

    messages = [{"role": m.role, "content": m.content} for m in req.messages]

    # Inject the most recently saved plan so the agent knows this week's meals
    current_plan = None
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
                current_plan = row[0]

    try:
        result = run_meal_agent(messages, PROFILES[req.person], current_plan=current_plan)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO agent_runs (agent_type, person_name, input_tokens, output_tokens, latency_ms)
                   VALUES (%s, %s, %s, %s, %s)""",
                ("meal_agent", req.person, result["input_tokens"], result["output_tokens"], result["latency_ms"]),
            )
        conn.commit()

    return {
        "message": result["message"],
        "meal_plan": result["meal_plan"],
        "recipe": result["recipe"],
    }


@app.post("/api/plans")
def save_plan(req: SavePlanRequest):
    if req.person not in PROFILES:
        raise HTTPException(status_code=400, detail=f"Unknown person: {req.person}")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO plans (person_name, type, content) VALUES (%s, %s, %s) RETURNING id",
                (req.person, "meal_plan", json.dumps(req.plan)),
            )
            plan_id = cur.fetchone()[0]
        conn.commit()

    return {"id": plan_id}


@app.get("/api/plans")
def list_plans(person: str):
    if person not in PROFILES:
        raise HTTPException(status_code=400, detail=f"Unknown person: {person}")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, person_name, content, created_at
                   FROM plans
                   WHERE person_name = %s AND type = 'meal_plan'
                   ORDER BY created_at DESC""",
                (person,),
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
