"""STUB — no real log backend exists yet. Replace with a real Cloud
Logging integration in Build Order step 5 (ARCHITECTURE.md §20). Returns
deterministic (in content, not wall-clock timestamp) fake log lines,
keyword-matched against the incident's trigger text via
app/tools/fake_data.py so the returned story actually relates to what
the incident describes, instead of always being the same fixed content.
"""

from datetime import UTC, datetime, timedelta

from app.models.schemas import LogEntry
from app.tools.fake_data import select_scenario


async def get_recent_logs(service: str, trigger: str = "", limit: int = 20) -> list[LogEntry]:
    scenario = select_scenario(trigger)
    now = datetime.now(UTC)
    entries = [
        LogEntry(
            timestamp=now - timedelta(minutes=minutes_ago),
            level=level,
            message=f"{service}: {message}",
        )
        for minutes_ago, level, message in scenario.log_lines
    ]
    return entries[:limit]
