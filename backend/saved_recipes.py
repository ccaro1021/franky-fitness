import json

from backend.database import get_connection


def save_recipe(user_id: int, recipe: dict) -> int:
    """Insert a saved recipe for a user, return its new id."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO saved_recipes (user_id, content) VALUES (%s, %s) RETURNING id",
                (user_id, json.dumps(recipe)),
            )
            recipe_id = cur.fetchone()[0]
        conn.commit()

    return recipe_id


def list_saved_recipes(user_id: int) -> list[dict]:
    """Return all saved recipes for a user, newest first."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, content, created_at FROM saved_recipes
                   WHERE user_id = %s ORDER BY created_at DESC""",
                (user_id,),
            )
            rows = cur.fetchall()

    return [{"id": r[0], "content": r[1], "created_at": r[2].isoformat()} for r in rows]


def delete_saved_recipe(recipe_id: int, user_id: int) -> bool:
    """Delete a saved recipe owned by user_id. Returns True if a row was deleted."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM saved_recipes WHERE id = %s AND user_id = %s",
                (recipe_id, user_id),
            )
            deleted = cur.rowcount > 0
        conn.commit()

    return deleted
