"""One-time migration: add users/profiles/sessions tables, create real accounts for
Chris & Kaitlyn (seeded from the old hardcoded profiles), and convert
plans/agent_runs/feedback/preference_summaries from person_name to user_id.

Run once: python -m backend.migrate_to_auth
"""

import getpass
import json

from backend.auth import hash_password
from backend.database import get_connection, setup_tables

SEED_PROFILES = {
    "Chris": {
        "dietary_restrictions": [],
        "fitness_goals": ["lose fat", "build muscle", "lower blood pressure risk", "lower diabetes risk"],
        "notes": "",
    },
    "Kaitlyn": {
        "dietary_restrictions": [],
        "fitness_goals": ["lose fat", "build muscle", "lower blood pressure risk", "lower diabetes risk"],
        "notes": "",
    },
}

LEGACY_TABLES = ("plans", "agent_runs", "feedback", "preference_summaries")


def _column_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """SELECT 1 FROM information_schema.columns
           WHERE table_name = %s AND column_name = %s""",
        (table, column),
    )
    return cur.fetchone() is not None


def main():
    print("Setting up users/profiles/sessions tables...")
    setup_tables()

    with get_connection() as conn:
        with conn.cursor() as cur:
            needs_migration = _column_exists(cur, "plans", "person_name")

    if not needs_migration:
        print("No person_name columns found — nothing to migrate.")
        return

    # Add nullable user_id columns to the legacy tables
    with get_connection() as conn:
        with conn.cursor() as cur:
            for table in LEGACY_TABLES:
                if _column_exists(cur, table, "person_name") and not _column_exists(cur, table, "user_id"):
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES users(id)")
        conn.commit()

    # Create real accounts for Chris & Kaitlyn, seeded from the old hardcoded profiles
    name_to_user_id: dict[str, int] = {}
    for name, seed in SEED_PROFILES.items():
        print(f"\nCreate account for {name}:")
        email = input(f"  Email for {name}: ").strip()
        password = getpass.getpass(f"  Password for {name}: ")

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (email, name, password_hash) VALUES (%s, %s, %s) RETURNING id",
                    (email, name, hash_password(password)),
                )
                user_id = cur.fetchone()[0]
                cur.execute(
                    """INSERT INTO profiles (user_id, dietary_restrictions, fitness_goals, notes)
                       VALUES (%s, %s, %s, %s)""",
                    (
                        user_id,
                        json.dumps(seed["dietary_restrictions"]),
                        json.dumps(seed["fitness_goals"]),
                        seed["notes"],
                    ),
                )
            conn.commit()

        name_to_user_id[name] = user_id
        print(f"  Created user id={user_id} ({email})")

    # Backfill user_id from person_name
    with get_connection() as conn:
        with conn.cursor() as cur:
            for table in LEGACY_TABLES:
                for name, user_id in name_to_user_id.items():
                    cur.execute(f"UPDATE {table} SET user_id = %s WHERE person_name = %s", (user_id, name))
        conn.commit()

    # Drop person_name and enforce NOT NULL / fix preference_summaries' primary key
    with get_connection() as conn:
        with conn.cursor() as cur:
            for table in ("plans", "agent_runs", "feedback"):
                cur.execute(f"ALTER TABLE {table} ALTER COLUMN user_id SET NOT NULL")
                cur.execute(f"ALTER TABLE {table} DROP COLUMN person_name")

            cur.execute("ALTER TABLE preference_summaries DROP CONSTRAINT preference_summaries_pkey")
            cur.execute("ALTER TABLE preference_summaries ALTER COLUMN user_id SET NOT NULL")
            cur.execute("ALTER TABLE preference_summaries ADD PRIMARY KEY (user_id)")
            cur.execute("ALTER TABLE preference_summaries DROP COLUMN person_name")
        conn.commit()

    print("\nMigration complete. Accounts created:")
    for name, user_id in name_to_user_id.items():
        print(f"  {name}: user_id={user_id}")


if __name__ == "__main__":
    main()
