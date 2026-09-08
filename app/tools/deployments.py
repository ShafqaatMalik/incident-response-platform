"""STUB — no real deployment history backend exists yet. Replace with a
real Cloud Run revision history integration in Build Order step 5
(ARCHITECTURE.md §20). Returns deterministic (in content, not wall-clock
timestamp) fake deployment events, keyword-matched against the
incident's trigger text via app/tools/fake_data.py so the returned
story actually relates to what the incident describes, instead of
always being the same fixed content.
"""

from datetime import UTC, datetime, timedelta

from app.models.schemas import DeploymentEvent
from app.tools.fake_data import OLD_DEPLOYMENT, select_scenario


async def get_deployment_history(
    service: str, trigger: str = "", limit: int = 5
) -> list[DeploymentEvent]:
    scenario = select_scenario(trigger)
    now = datetime.now(UTC)
    events: list[DeploymentEvent] = []

    if scenario.deployment is not None:
        minutes_ago, version, description = scenario.deployment
        events.append(
            DeploymentEvent(
                timestamp=now - timedelta(minutes=minutes_ago),
                version=version,
                description=f"Deploy {service}: {description}",
            )
        )

    old_minutes_ago, old_version, old_description = OLD_DEPLOYMENT
    events.append(
        DeploymentEvent(
            timestamp=now - timedelta(minutes=old_minutes_ago),
            version=old_version,
            description=f"Deploy {service}: {old_description}",
        )
    )

    return events[:limit]
