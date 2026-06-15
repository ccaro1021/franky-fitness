import json

from backend.database import get_connection


def compute_bmi(height_inches: float | None, weight_lbs: float | None) -> float | None:
    """Compute BMI from height (inches) and weight (lbs), or None if either is missing."""
    if not height_inches or not weight_lbs:
        return None
    return round(weight_lbs / (height_inches ** 2) * 703, 1)


def create_user(email: str, name: str, password_hash: str) -> dict:
    """Create a new user with an empty profile row, return {id, email, name}."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (email, name, password_hash) VALUES (%s, %s, %s) RETURNING id",
                (email, name, password_hash),
            )
            user_id = cur.fetchone()[0]
            cur.execute("INSERT INTO profiles (user_id) VALUES (%s)", (user_id,))
        conn.commit()

    return {"id": user_id, "email": email, "name": name}


def get_user_by_email(email: str) -> dict | None:
    """Return {id, email, name, password_hash} for a user by email, or None."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, name, password_hash FROM users WHERE email = %s",
                (email,),
            )
            row = cur.fetchone()

    if not row:
        return None

    return {"id": row[0], "email": row[1], "name": row[2], "password_hash": row[3]}


def get_profile(user_id: int) -> dict:
    """Return the stored profile for a user, with bmi computed from height/weight."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT height_inches, weight_lbs, target_weight_lbs,
                          dietary_restrictions, fitness_goals, notes
                   FROM profiles WHERE user_id = %s""",
                (user_id,),
            )
            row = cur.fetchone()

    height_inches, weight_lbs, target_weight_lbs, dietary_restrictions, fitness_goals, notes = row

    return {
        "height_inches": height_inches,
        "weight_lbs": weight_lbs,
        "target_weight_lbs": target_weight_lbs,
        "dietary_restrictions": dietary_restrictions,
        "fitness_goals": fitness_goals,
        "notes": notes,
        "bmi": compute_bmi(height_inches, weight_lbs),
    }


def update_profile(
    user_id: int,
    height_inches: float | None,
    weight_lbs: float | None,
    target_weight_lbs: float | None,
    dietary_restrictions: list[str],
    fitness_goals: list[str],
    notes: str,
) -> dict:
    """Update a user's profile and return the refreshed profile (with computed bmi)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE profiles SET
                       height_inches = %s,
                       weight_lbs = %s,
                       target_weight_lbs = %s,
                       dietary_restrictions = %s,
                       fitness_goals = %s,
                       notes = %s,
                       updated_at = NOW()
                   WHERE user_id = %s""",
                (
                    height_inches,
                    weight_lbs,
                    target_weight_lbs,
                    json.dumps(dietary_restrictions),
                    json.dumps(fitness_goals),
                    notes,
                    user_id,
                ),
            )
        conn.commit()

    return get_profile(user_id)


def patch_profile(user_id: int, **fields) -> dict:
    """Partially update a user's profile: overwrite scalar fields if provided, merge/dedupe
    list fields (add_dietary_restrictions/add_fitness_goals), and append append_notes on a
    new line. Fields not present in `fields` are left untouched. Returns the refreshed profile."""
    current = get_profile(user_id)

    sets = []
    params = []

    for scalar_field in ("height_inches", "weight_lbs", "target_weight_lbs"):
        if scalar_field in fields:
            sets.append(f"{scalar_field} = %s")
            params.append(fields[scalar_field])

    for list_field, source_key in (
        ("dietary_restrictions", "add_dietary_restrictions"),
        ("fitness_goals", "add_fitness_goals"),
    ):
        if source_key in fields:
            existing = current[list_field] or []
            existing_lower = {item.lower() for item in existing}
            merged = list(existing)
            for item in fields[source_key]:
                if item.lower() not in existing_lower:
                    merged.append(item)
                    existing_lower.add(item.lower())
            sets.append(f"{list_field} = %s")
            params.append(json.dumps(merged))

    if "append_notes" in fields:
        existing_notes = current.get("notes") or ""
        new_notes = f"{existing_notes}\n{fields['append_notes']}" if existing_notes else fields["append_notes"]
        sets.append("notes = %s")
        params.append(new_notes)

    if not sets:
        return current

    sets.append("updated_at = NOW()")
    params.append(user_id)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE profiles SET {', '.join(sets)} WHERE user_id = %s",
                params,
            )
        conn.commit()

    return get_profile(user_id)


def build_profile_context(user_id: int) -> dict:
    """Build the profile dict shape expected by the agents' system prompts."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT name FROM users WHERE id = %s", (user_id,))
            name = cur.fetchone()[0]

    profile = get_profile(user_id)
    return {"name": name, **profile}
