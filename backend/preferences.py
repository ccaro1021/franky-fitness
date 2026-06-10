import json

from backend.database import get_connection

ITEM_TYPES = ("meal", "exercise")
RATINGS = ("positive", "negative")


def record_feedback(
    person_name: str,
    plan_id: int | None,
    item_type: str,
    item_name: str,
    rating: str,
    note: str | None,
) -> dict:
    """Insert a feedback row and recompute the person's preference summary."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO feedback (person_name, plan_id, item_type, item_name, rating, note)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (person_name, plan_id, item_type, item_name, rating, note),
            )
        conn.commit()

    return _recompute_summary(person_name)


def _recompute_summary(person_name: str) -> dict:
    """Recompute and store the preference summary from the full feedback history."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT DISTINCT ON (item_type, item_name) item_type, item_name, rating
                   FROM feedback
                   WHERE person_name = %s
                   ORDER BY item_type, item_name, created_at DESC""",
                (person_name,),
            )
            rows = cur.fetchall()

            summary = {
                "liked_meals": [],
                "disliked_meals": [],
                "liked_workouts": [],
                "disliked_workouts": [],
                "patterns": [],
            }
            for item_type, item_name, rating in rows:
                if item_type == "meal":
                    bucket = "liked_meals" if rating == "positive" else "disliked_meals"
                else:
                    bucket = "liked_workouts" if rating == "positive" else "disliked_workouts"
                summary[bucket].append(item_name)

            cur.execute(
                """INSERT INTO preference_summaries (person_name, summary, updated_at)
                   VALUES (%s, %s, NOW())
                   ON CONFLICT (person_name) DO UPDATE SET summary = EXCLUDED.summary, updated_at = NOW()""",
                (person_name, json.dumps(summary)),
            )
        conn.commit()

    return summary


def get_preference_summary(person_name: str) -> dict | None:
    """Return the stored preference summary for a person, or None if no feedback yet."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT summary FROM preference_summaries WHERE person_name = %s",
                (person_name,),
            )
            row = cur.fetchone()

    return row[0] if row else None
