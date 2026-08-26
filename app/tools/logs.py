"""STUB — no real log backend exists yet. Replace with a real Cloud Logging
integration in Build Order step 5 (ARCHITECTURE.md §20). Returns
deterministic (in content, not wall-clock timestamp) fake log lines,
correlated with app/tools/deployments.py's fake deployment, so the
Investigation Agent has something coherent to reason about.
"""

from datetime import UTC, datetime, timedelta

from app.models.schemas import LogEntry


async def get_recent_logs(service: str, limit: int = 20) -> list[LogEntry]:
    now = datetime.now(UTC)
    entries = [
        LogEntry(
            timestamp=now - timedelta(minutes=2),
            level="ERROR",
            message=f"{service}: connection pool exhausted, 0 available connections",
        ),
        LogEntry(
            timestamp=now - timedelta(minutes=3),
            level="ERROR",
            message=f"{service}: request to database timed out after 5000ms",
        ),
        LogEntry(
            timestamp=now - timedelta(minutes=5),
            level="WARN",
            message=f"{service}: elevated response latency detected",
        ),
        LogEntry(
            timestamp=now - timedelta(minutes=7),
            level="INFO",
            message=f"{service}: connection pool size reduced during rolling restart",
        ),
    ]
    return entries[:limit]
