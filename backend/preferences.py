import json

from backend.database import get_connection

ITEM_TYPES = ("meal", "exercise")
RATINGS = ("positive", "negative")

EMPTY_SUMMARY = {
    "liked_meals": [],
    "disliked_meals": [],
    "liked_workouts": [],
    "disliked_workouts": [],
    "patterns": [],
}


def record_feedback(
    user_id: int,
    plan_id: int | None,
    item_type: str,
    item_name: str,
    rating: str,
    note: str | None,
) -> dict:
    """Insert a feedback row and recompute the user's preference summary."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO feedback (user_id, plan_id, item_type, item_name, rating, note)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (user_id, plan_id, item_type, item_name, rating, note),
            )
        conn.commit()

    return _recompute_summary(user_id)


def _recompute_summary(user_id: int) -> dict:
    """Recompute and store the preference summary from the full feedback history."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT DISTINCT ON (item_type, item_name) item_type, item_name, rating
                   FROM feedback
                   WHERE user_id = %s
                   ORDER BY item_type, item_name, created_at DESC""",
                (user_id,),
            )
            rows = cur.fetchall()

            summary = {key: [] for key in EMPTY_SUMMARY}
            for item_type, item_name, rating in rows:
                if item_type == "meal":
                    bucket = "liked_meals" if rating == "positive" else "disliked_meals"
                else:
                    bucket = "liked_workouts" if rating == "positive" else "disliked_workouts"
                summary[bucket].append(item_name)

            cur.execute(
                """INSERT INTO preference_summaries (user_id, summary, updated_at)
                   VALUES (%s, %s, NOW())
                   ON CONFLICT (user_id) DO UPDATE SET summary = EXCLUDED.summary, updated_at = NOW()""",
                (user_id, json.dumps(summary)),
            )
        conn.commit()

    return summary


def get_preference_summary(user_id: int) -> dict | None:
    """Return the stored preference summary for a user, or None if no feedback yet."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT summary FROM preference_summaries WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()

    return row[0] if row else None


def forget_item(user_id: int, item_type: str, item_name: str) -> dict:
    """Delete all feedback for an item and recompute the user's preference summary."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM feedback WHERE user_id = %s AND item_type = %s AND item_name = %s",
                (user_id, item_type, item_name),
            )
        conn.commit()

    return _recompute_summary(user_id)
