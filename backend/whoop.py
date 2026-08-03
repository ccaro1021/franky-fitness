import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

from backend.database import get_connection

load_dotenv()

WHOOP_AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
WHOOP_SCOPES = "read:recovery read:cycles read:sleep read:workout read:profile read:body_measurement offline"

_CLIENT_ID = os.getenv("WHOOP_CLIENT_ID")
_CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET")
_REDIRECT_URI = os.getenv("WHOOP_REDIRECT_URI")

STATE_TTL = timedelta(minutes=10)


def create_oauth_state(user_id: int) -> str:
    """Generate and store a CSRF state token tied to a user for the WHOOP OAuth flow."""
    state = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + STATE_TTL
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO whoop_oauth_states (state, user_id, expires_at) VALUES (%s, %s, %s)",
                (state, user_id, expires_at),
            )
        conn.commit()
    return state


def consume_oauth_state(state: str) -> int | None:
    """Validate and delete a state token; return its user_id, or None if invalid/expired."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM whoop_oauth_states WHERE state = %s AND expires_at > NOW() RETURNING user_id",
                (state,),
            )
            row = cur.fetchone()
        conn.commit()
    return row[0] if row else None


def get_authorization_url(state: str) -> str:
    """Build the WHOOP authorization redirect URL for a given state token."""
    if not _CLIENT_ID or not _REDIRECT_URI:
        raise RuntimeError("WHOOP_CLIENT_ID and WHOOP_REDIRECT_URI must be set in .env")
    params = {
        "client_id": _CLIENT_ID,
        "redirect_uri": _REDIRECT_URI,
        "response_type": "code",
        "scope": WHOOP_SCOPES,
        "state": state,
    }
    return f"{WHOOP_AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str) -> dict:
    """Exchange an authorization code for WHOOP access + refresh tokens."""
    if not _CLIENT_ID or not _CLIENT_SECRET or not _REDIRECT_URI:
        raise RuntimeError("WHOOP_CLIENT_ID, WHOOP_CLIENT_SECRET, and WHOOP_REDIRECT_URI must be set in .env")
    try:
        response = requests.post(
            WHOOP_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": _REDIRECT_URI,
                "client_id": _CLIENT_ID,
                "client_secret": _CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"WHOOP token exchange failed: {e}") from e


def store_whoop_tokens(user_id: int, token_data: dict) -> None:
    """Upsert WHOOP OAuth tokens for a user."""
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data.get("expires_in", 3600))
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO whoop_tokens
                       (user_id, access_token, refresh_token, token_type, scope, expires_at)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   ON CONFLICT (user_id) DO UPDATE SET
                       access_token = EXCLUDED.access_token,
                       refresh_token = EXCLUDED.refresh_token,
                       token_type = EXCLUDED.token_type,
                       scope = EXCLUDED.scope,
                       expires_at = EXCLUDED.expires_at,
                       updated_at = NOW()""",
                (
                    user_id,
                    token_data["access_token"],
                    token_data.get("refresh_token"),
                    token_data.get("token_type", "Bearer"),
                    token_data.get("scope", WHOOP_SCOPES),
                    expires_at,
                ),
            )
        conn.commit()


def get_whoop_tokens(user_id: int) -> dict | None:
    """Return stored WHOOP tokens for a user, or None if not connected."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT access_token, refresh_token, token_type, scope, expires_at
                   FROM whoop_tokens WHERE user_id = %s""",
                (user_id,),
            )
            row = cur.fetchone()
    if not row:
        return None
    return {
        "access_token": row[0],
        "refresh_token": row[1],
        "token_type": row[2],
        "scope": row[3],
        "expires_at": row[4].isoformat(),
    }


def refresh_whoop_token(user_id: int) -> dict:
    """Exchange the stored refresh token for a new access token and update the DB.

    WHOOP invalidates the old access token as soon as the refresh token is used,
    so we upsert the new token data immediately. Raises RuntimeError if the user
    has no stored tokens, has no refresh token, or if the WHOOP request fails.
    """
    if not _CLIENT_ID or not _CLIENT_SECRET:
        raise RuntimeError("WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET must be set in .env")

    tokens = get_whoop_tokens(user_id)
    if not tokens:
        raise RuntimeError("No WHOOP tokens found — user must connect their account first")
    if not tokens.get("refresh_token"):
        raise RuntimeError("No refresh token stored — user must reconnect their WHOOP account")

    try:
        response = requests.post(
            WHOOP_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": tokens["refresh_token"],
                "client_id": _CLIENT_ID,
                "client_secret": _CLIENT_SECRET,
                "scope": "offline",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10,
        )
        response.raise_for_status()
        token_data = response.json()
    except requests.RequestException as e:
        raise RuntimeError(f"WHOOP token refresh failed: {e}") from e

    store_whoop_tokens(user_id, token_data)
    return token_data
