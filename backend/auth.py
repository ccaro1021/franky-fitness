import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import HTTPException, Request

from backend.database import get_connection

SESSION_TTL = timedelta(days=30)


def hash_password(password: str) -> str:
    """Hash a plaintext password for storage."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plaintext password against a stored hash."""
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_session(user_id: int) -> str:
    """Create a new session for a user and return its token."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + SESSION_TTL

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (token, user_id, expires_at) VALUES (%s, %s, %s)",
                (token, user_id, expires_at),
            )
        conn.commit()

    return token


def get_user_by_session(token: str) -> dict | None:
    """Return the user for a valid, unexpired session token, or None."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT users.id, users.email, users.name
                   FROM sessions
                   JOIN users ON users.id = sessions.user_id
                   WHERE sessions.token = %s AND sessions.expires_at > NOW()""",
                (token,),
            )
            row = cur.fetchone()

    if not row:
        return None

    return {"id": row[0], "email": row[1], "name": row[2]}


def delete_session(token: str) -> None:
    """Delete a session, e.g. on logout."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE token = %s", (token,))
        conn.commit()


def get_current_user(request: Request) -> dict:
    """FastAPI dependency: resolve the logged-in user from the session cookie."""
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = get_user_by_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    return user
