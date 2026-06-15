"""One-time migration: clear cached `category` fields on meal plan ingredients so the
next grocery-list request re-runs reconcile_quantities with the new category set
(produce/fruit/protein/dairy_eggs/carbs/pantry instead of the old
produce/protein/dairy/frozen/pantry).

Run once: python -m backend.migrate_grocery_categories
"""

import json

from backend.database import get_connection


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, content FROM plans WHERE type = 'meal_plan'")
            rows = cur.fetchall()

            updated = 0
            for plan_id, content in rows:
                changed = False
                for meal in content.get("meals", []):
                    for ingredient in meal.get("ingredients", []):
                        if ingredient.pop("category", None) is not None:
                            changed = True
                if changed:
                    cur.execute("UPDATE plans SET content = %s WHERE id = %s", (json.dumps(content), plan_id))
                    updated += 1

        conn.commit()

    print(f"Cleared cached categories on {updated} plan(s).")


if __name__ == "__main__":
    main()
