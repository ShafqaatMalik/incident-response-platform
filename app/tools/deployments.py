"""STUB — no real deployment history backend exists yet. Replace with a
real Cloud Run revision history integration in Build Order step 5
(ARCHITECTURE.md §20). Returns deterministic (in content, not wall-clock
timestamp) fake deployment events, correlated with app/tools/logs.py's
fake log lines, so the Investigation Agent has something coherent to
reason about.
"""

from datetime import UTC, datetime, timedelta

from app.models.schemas import DeploymentEvent


async def get_deployment_history(service: str, limit: int = 5) -> list[DeploymentEvent]:
    now = datetime.now(UTC)
    events = [
        DeploymentEvent(
            timestamp=now - timedelta(minutes=8),
            version="v1.42.0",
            description=f"Deploy {service}: bump database driver and reduce connection pool size",
        ),
        DeploymentEvent(
            timestamp=now - timedelta(days=2),
            version="v1.41.3",
            description=f"Deploy {service}: minor logging improvements",
        ),
    ]
    return events[:limit]
