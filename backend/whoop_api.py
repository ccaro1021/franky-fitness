import os
from datetime import datetime, timezone, timedelta

import requests
from dotenv import load_dotenv

from backend.database import get_connection
from backend.whoop import WHOOP_TOKEN_URL, store_whoop_tokens

load_dotenv()

WHOOP_API_BASE = "https://api.prod.whoop.com/developer/v2"


def get_valid_access_token(user_id: int) -> str | None:
    """Return a valid WHOOP access token for a user, refreshing under a row-level lock if within 5 min of expiry."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT access_token, refresh_token, expires_at FROM whoop_tokens WHERE user_id = %s FOR UPDATE",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                conn.commit()
                return None
            access_token, refresh_token, expires_at = row

            if expires_at - datetime.now(timezone.utc) > timedelta(minutes=5):
                conn.commit()
                return access_token

            # Token expiring soon — refresh under the lock so concurrent requests don't race
            try:
                resp = requests.post(
                    WHOOP_TOKEN_URL,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                        "client_id": os.getenv("WHOOP_CLIENT_ID"),
                        "client_secret": os.getenv("WHOOP_CLIENT_SECRET"),
                        "scope": "offline",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10,
                )
                resp.raise_for_status()
                token_data = resp.json()
                new_expires_at = datetime.now(timezone.utc) + timedelta(
                    seconds=token_data.get("expires_in", 3600)
                )
                cur.execute(
                    """UPDATE whoop_tokens
                       SET access_token = %s, refresh_token = %s, token_type = %s,
                           scope = %s, expires_at = %s, updated_at = NOW()
                       WHERE user_id = %s""",
                    (
                        token_data["access_token"],
                        token_data.get("refresh_token"),
                        token_data.get("token_type", "Bearer"),
                        token_data.get("scope"),
                        new_expires_at,
                        user_id,
                    ),
                )
                conn.commit()
                return token_data["access_token"]
            except Exception:
                conn.rollback()
                return None


def get_latest_recovery(access_token: str) -> dict | None:
    """GET /v2/recovery — recovery score, HRV, resting heart rate. Returns None on failure or no data."""
    try:
        r = requests.get(
            f"{WHOOP_API_BASE}/recovery",
            params={"limit": 1},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=8,
        )
        r.raise_for_status()
        records = r.json().get("records", [])
        if not records:
            return None
        rec = records[0]
        s = rec.get("score", {})
        return {
            "recovery_score": s.get("recovery_score"),
            "hrv_rmssd_milli": s.get("hrv_rmssd_milli"),
            "resting_heart_rate": s.get("resting_heart_rate"),
            "score_state": rec.get("score_state"),
        }
    except requests.RequestException:
        return None


def get_latest_sleep(access_token: str) -> dict | None:
    """GET /v2/activity/sleep — sleep performance and total hours. Returns None on failure or no data."""
    try:
        r = requests.get(
            f"{WHOOP_API_BASE}/activity/sleep",
            params={"limit": 1},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=8,
        )
        r.raise_for_status()
        records = r.json().get("records", [])
        if not records:
            return None
        rec = records[0]
        s = rec.get("score", {})
        stage = s.get("stage_summary", {})
        total_ms = stage.get("total_in_bed_time_milli", 0)
        return {
            "sleep_performance_percentage": s.get("sleep_performance_percentage"),
            "total_hours": round(total_ms / 3_600_000, 1) if total_ms else None,
            "score_state": rec.get("score_state"),
        }
    except requests.RequestException:
        return None


def get_recent_workouts_data(access_token: str, days: int = 7) -> list[dict]:
    """GET /v2/activity/workout filtered by start date — recent workout strain data."""
    start = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        r = requests.get(
            f"{WHOOP_API_BASE}/activity/workout",
            params={"start": start, "limit": 25},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=8,
        )
        r.raise_for_status()
        records = r.json().get("records", [])
        return [
            {
                "strain": rec.get("score", {}).get("strain"),
                "created_at": rec.get("created_at"),
                "score_state": rec.get("score_state"),
            }
            for rec in records
        ]
    except requests.RequestException:
        return []
