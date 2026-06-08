import os
import requests
from dotenv import load_dotenv
from models import Exercise

load_dotenv()

BASE_URL = "https://exercisedb.p.rapidapi.com"
HEADERS = {
    "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
    "X-RapidAPI-Host": "exercisedb.p.rapidapi.com",
}


def search_exercises(
    name: str = "",
    body_part: str = "",
    target_muscle: str = "",
    equipment: str = "",
    limit: int = 8,
) -> list[Exercise]:
    # Priority: name > target_muscle > body_part > equipment
    if name:
        url = f"{BASE_URL}/exercises/name/{name.lower()}"
    elif target_muscle:
        url = f"{BASE_URL}/exercises/target/{target_muscle.lower()}"
    elif body_part:
        url = f"{BASE_URL}/exercises/bodyPart/{body_part.lower()}"
    elif equipment:
        url = f"{BASE_URL}/exercises/equipment/{equipment.lower()}"
    else:
        url = f"{BASE_URL}/exercises"

    response = requests.get(url, headers=HEADERS, params={"limit": limit, "offset": 0})
    response.raise_for_status()
    return [_map_to_exercise(e) for e in response.json()[:limit]]


def get_exercise(exercise_id: str) -> Exercise:
    response = requests.get(f"{BASE_URL}/exercises/exercise/{exercise_id}", headers=HEADERS)
    response.raise_for_status()
    return _map_to_exercise(response.json())


def _map_to_exercise(data: dict) -> Exercise:
    return Exercise(
        id=data["id"],
        name=data["name"],
        body_part=data["bodyPart"],
        equipment=data["equipment"],
        target_muscle=data["target"],
        secondary_muscles=data.get("secondaryMuscles", []),
        instructions=data.get("instructions", []),
        gif_url=data.get("gifUrl", ""),
    )
