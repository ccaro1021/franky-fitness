"""Integration tests for saved recipes and plan deletion (Slice 11).

Black-box over HTTP via FastAPI's TestClient, run against the local
`franky_fitness` Postgres database (no separate test-DB infra exists yet,
consistent with local-dev-DB usage elsewhere). Each test signs up a
throwaway user and cleans up the rows it creates.

Run from the repo root: `python -m unittest tests.test_saved_items`
"""

import unittest
import uuid

from fastapi.testclient import TestClient

from backend.main import app

SAMPLE_RECIPE = {
    "name": "Grilled Chicken Bowl",
    "calories_per_serving": 450,
    "protein_g": 40,
    "carbs_g": 35,
    "fat_g": 12,
    "recipe": "1. Grill the chicken.\n2. Serve over rice.",
    "ingredients": [
        {"name": "chicken breast", "quantity_per_serving": 6, "unit": "oz"},
        {"name": "rice", "quantity_per_serving": 1, "unit": "cup"},
    ],
    "spoonacular_id": 12345,
}

SAMPLE_MEAL_PLAN = {
    "meals": [
        {
            "day": "Monday",
            "meal_type": "dinner",
            "name": "Grilled Chicken Bowl",
            "calories": 450,
            "protein_g": 40,
            "carbs_g": 35,
            "fat_g": 12,
            "spoonacular_id": 12345,
            "ingredients_fetched": False,
        }
    ],
    "notes": "",
}

SAMPLE_WORKOUT_PLAN = {
    "workout_days": [
        {
            "day": "Monday",
            "focus": "Full Body",
            "exercises": [
                {
                    "exercise_id": "0001",
                    "exercise_name": "Push-up",
                    "sets": 3,
                    "reps": "10-12",
                    "rest_seconds": 60,
                }
            ],
        }
    ],
    "rest_days": ["Sunday"],
    "notes": "",
}


def _signup(client: TestClient) -> dict:
    email = f"test-{uuid.uuid4().hex[:12]}@example.com"
    res = client.post(
        "/api/auth/signup",
        json={"email": email, "password": "testpass123", "name": "Test User"},
    )
    assert res.status_code == 200, res.text
    return res.json()


class SavedRecipesTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        _signup(self.client)

    def test_save_list_and_delete_recipe(self):
        res = self.client.post("/api/saved-recipes", json=SAMPLE_RECIPE)
        self.assertEqual(res.status_code, 200, res.text)
        recipe_id = res.json()["id"]

        res = self.client.get("/api/saved-recipes")
        self.assertEqual(res.status_code, 200, res.text)
        saved = res.json()
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["id"], recipe_id)
        self.assertEqual(saved[0]["content"]["name"], "Grilled Chicken Bowl")

        res = self.client.delete(f"/api/saved-recipes/{recipe_id}")
        self.assertEqual(res.status_code, 200, res.text)

        res = self.client.get("/api/saved-recipes")
        self.assertEqual(res.json(), [])

    def test_save_same_recipe_twice_creates_two_rows(self):
        first = self.client.post("/api/saved-recipes", json=SAMPLE_RECIPE)
        second = self.client.post("/api/saved-recipes", json=SAMPLE_RECIPE)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertNotEqual(first.json()["id"], second.json()["id"])

        res = self.client.get("/api/saved-recipes")
        self.assertEqual(len(res.json()), 2)

        for recipe_id in (first.json()["id"], second.json()["id"]):
            self.client.delete(f"/api/saved-recipes/{recipe_id}")


class PlanDeletionTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        _signup(self.client)

    def test_delete_meal_plan(self):
        res = self.client.post("/api/plans", json={"plan": SAMPLE_MEAL_PLAN, "type": "meal_plan"})
        self.assertEqual(res.status_code, 200, res.text)
        plan_id = res.json()["id"]

        res = self.client.delete(f"/api/plans/{plan_id}")
        self.assertEqual(res.status_code, 200, res.text)

        res = self.client.get(f"/api/plans/{plan_id}")
        self.assertEqual(res.status_code, 404)

    def test_delete_workout_plan(self):
        res = self.client.post("/api/plans", json={"plan": SAMPLE_WORKOUT_PLAN, "type": "workout_plan"})
        self.assertEqual(res.status_code, 200, res.text)
        plan_id = res.json()["id"]

        res = self.client.delete(f"/api/plans/{plan_id}")
        self.assertEqual(res.status_code, 200, res.text)

        res = self.client.get(f"/api/plans/{plan_id}")
        self.assertEqual(res.status_code, 404)

    def test_delete_nonexistent_plan_404(self):
        res = self.client.delete("/api/plans/999999999")
        self.assertEqual(res.status_code, 404)


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.client_a = TestClient(app)
        _signup(self.client_a)
        self.client_b = TestClient(app)
        _signup(self.client_b)

    def test_cannot_delete_another_users_plan(self):
        res = self.client_a.post("/api/plans", json={"plan": SAMPLE_MEAL_PLAN, "type": "meal_plan"})
        plan_id = res.json()["id"]

        res = self.client_b.delete(f"/api/plans/{plan_id}")
        self.assertEqual(res.status_code, 404)

        # still owned by client_a
        res = self.client_a.get(f"/api/plans/{plan_id}")
        self.assertEqual(res.status_code, 200)

        self.client_a.delete(f"/api/plans/{plan_id}")

    def test_cannot_delete_another_users_recipe(self):
        res = self.client_a.post("/api/saved-recipes", json=SAMPLE_RECIPE)
        recipe_id = res.json()["id"]

        res = self.client_b.delete(f"/api/saved-recipes/{recipe_id}")
        self.assertEqual(res.status_code, 404)

        res = self.client_a.get("/api/saved-recipes")
        self.assertEqual(len(res.json()), 1)

        self.client_a.delete(f"/api/saved-recipes/{recipe_id}")


if __name__ == "__main__":
    unittest.main()
