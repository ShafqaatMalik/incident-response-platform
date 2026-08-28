from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident, IncidentStatus
from app.orchestration.state_machine import transition


async def run_approval(incident: Incident, approved_by: str, session: AsyncSession) -> Incident:
    transition(incident, IncidentStatus.APPROVED)
    incident.approved_by = approved_by
    incident.approved_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(incident)
    return incident


async def run_rejection(
    incident: Incident, rejected_by: str, rejection_reason: str, session: AsyncSession
) -> Incident:
    transition(incident, IncidentStatus.REJECTED)
    incident.rejected_by = rejected_by
    incident.rejected_at = datetime.now(UTC)
    incident.rejection_reason = rejection_reason

    await session.commit()
    await session.refresh(incident)
    return incident
