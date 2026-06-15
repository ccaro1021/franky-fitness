"""DB-backed tests for backend.users.patch_profile (Slice 13).

Mirrors tests/test_saved_items.py's pattern of using a real local Postgres
connection via unittest. Each test signs up a throwaway user via the API
(to get a user_id) and exercises patch_profile directly.

Run from the repo root: `python -m unittest tests.test_users`
"""

import unittest
import uuid

from fastapi.testclient import TestClient

from backend.main import app
from backend.users import get_profile, patch_profile


def _signup(client: TestClient) -> dict:
    email = f"test-{uuid.uuid4().hex[:12]}@example.com"
    res = client.post(
        "/api/auth/signup",
        json={"email": email, "password": "testpass123", "name": "Test User"},
    )
    assert res.status_code == 200, res.text
    return res.json()


class PatchProfileTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        user = _signup(self.client)
        self.user_id = user["id"]

    def test_overwrites_scalar_fields_when_provided(self):
        updated = patch_profile(self.user_id, height_inches=70, weight_lbs=190, target_weight_lbs=175)
        self.assertEqual(updated["height_inches"], 70)
        self.assertEqual(updated["weight_lbs"], 190)
        self.assertEqual(updated["target_weight_lbs"], 175)

    def test_leaves_scalar_fields_untouched_when_omitted(self):
        patch_profile(self.user_id, height_inches=70, weight_lbs=190)
        updated = patch_profile(self.user_id, target_weight_lbs=175)
        self.assertEqual(updated["height_inches"], 70)
        self.assertEqual(updated["weight_lbs"], 190)
        self.assertEqual(updated["target_weight_lbs"], 175)

    def test_merges_and_dedupes_dietary_restrictions(self):
        patch_profile(self.user_id, add_dietary_restrictions=["vegetarian"])
        updated = patch_profile(self.user_id, add_dietary_restrictions=["Vegetarian", "shellfish allergy"])
        self.assertEqual(updated["dietary_restrictions"], ["vegetarian", "shellfish allergy"])

    def test_merges_and_dedupes_fitness_goals(self):
        patch_profile(self.user_id, add_fitness_goals=["lose fat"])
        updated = patch_profile(self.user_id, add_fitness_goals=["Lose Fat", "train for a 10k"])
        self.assertEqual(updated["fitness_goals"], ["lose fat", "train for a 10k"])

    def test_appends_notes_on_new_line(self):
        patch_profile(self.user_id, append_notes="Has a bad knee, go easy on lunges.")
        updated = patch_profile(self.user_id, append_notes="Prefers morning workouts.")
        self.assertEqual(
            updated["notes"],
            "Has a bad knee, go easy on lunges.\nPrefers morning workouts.",
        )

    def test_appending_to_empty_notes_has_no_leading_blank_line(self):
        updated = patch_profile(self.user_id, append_notes="First note.")
        self.assertEqual(updated["notes"], "First note.")

    def test_returned_shape_matches_get_profile(self):
        updated = patch_profile(self.user_id, height_inches=70, weight_lbs=190)
        self.assertEqual(set(updated.keys()), set(get_profile(self.user_id).keys()))
        self.assertIn("bmi", updated)
        self.assertIsNotNone(updated["bmi"])


if __name__ == "__main__":
    unittest.main()
