"""WHOOP biometric MCP server for Franky Fitness.

Exposes three tools: get_recovery, get_sleep, get_recent_workouts.
The WHOOP bearer token is read from the Authorization header (HTTP/SSE transport)
or from the WHOOP_AUTH_TOKEN environment variable (stdio transport).

Run in stdio mode (Phase A, for MCP Inspector or subprocess client):
    python -m backend.whoop_mcp_server

Run in SSE mode (Phase B, for Cloud Run):
    python -c "from backend.whoop_mcp_server import server; server.run(transport='sse', host='0.0.0.0', port=8080)"
"""
import os

from mcp.server import MCPServer
from mcp.server.mcpserver.context import Context

from backend.whoop_api import get_latest_recovery, get_latest_sleep, get_recent_workouts_data as _fetch_workouts

server = MCPServer(
    "whoop-franky",
    description="WHOOP biometric data (recovery, sleep, workouts) for Franky Fitness",
)


def _get_token(ctx: Context) -> str | None:
    """Extract bearer token: from Authorization header (HTTP/SSE) or WHOOP_AUTH_TOKEN env (stdio)."""
    headers = ctx.headers
    if headers:
        auth = headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth[7:].strip()
    return os.getenv("WHOOP_AUTH_TOKEN")


@server.tool(
    description=(
        "Get the user's latest WHOOP recovery score (0–100), HRV in milliseconds, "
        "and resting heart rate in bpm. Returns 'unavailable' if data is missing or not yet scored."
    ),
    structured_output=False,
)
def get_recovery(ctx: Context) -> str:
    token = _get_token(ctx)
    if not token:
        return "Authorization required — WHOOP not connected."
    data = get_latest_recovery(token)
    if not data or data.get("score_state") != "SCORED":
        return "Recovery data unavailable or not yet scored today."
    return (
        f"Recovery: {data['recovery_score']}% | "
        f"HRV: {data['hrv_rmssd_milli']:.1f}ms | "
        f"Resting HR: {data['resting_heart_rate']} bpm"
    )


@server.tool(
    description=(
        "Get the user's last night's WHOOP sleep performance percentage and total hours slept. "
        "Returns 'unavailable' if data is missing or not yet scored."
    ),
    structured_output=False,
)
def get_sleep(ctx: Context) -> str:
    token = _get_token(ctx)
    if not token:
        return "Authorization required — WHOOP not connected."
    data = get_latest_sleep(token)
    if not data or data.get("score_state") != "SCORED":
        return "Sleep data unavailable or not yet scored."
    return (
        f"Sleep performance: {data['sleep_performance_percentage']}% | "
        f"Total sleep: {data['total_hours']}h"
    )


@server.tool(
    description=(
        "Get the user's recent WHOOP workout strain data from the past N days. "
        "Strain is 0–21 (higher = more cumulative load). "
        "Returns 'no workouts' if none were recorded in that window."
    ),
    structured_output=False,
)
def get_recent_workouts(ctx: Context, days: int = 7) -> str:
    token = _get_token(ctx)
    if not token:
        return "Authorization required — WHOOP not connected."
    workouts = _fetch_workouts(token, days=days)
    if not workouts:
        return f"No WHOOP workouts recorded in the past {days} days."
    lines = [f"Workouts in the past {days} days:"]
    for w in workouts[:10]:
        date = (w.get("created_at") or "")[:10]
        strain = w.get("strain")
        lines.append(f"  {date}: strain {strain:.1f}" if strain else f"  {date}: strain unavailable")
    return "\n".join(lines)


if __name__ == "__main__":
    server.run()  # stdio mode
