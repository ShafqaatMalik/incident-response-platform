from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident, IncidentStatus
from app.orchestration.state_machine import transition, validate_transition
from app.policies.validation_policy import validate_remediation


async def run_validation(incident: Incident, session: AsyncSession) -> Incident:
    validate_transition(incident, IncidentStatus.AWAITING_APPROVAL)

    result = validate_remediation(incident)
    if result.passed:
        transition(incident, IncidentStatus.AWAITING_APPROVAL)
    else:
        transition(incident, IncidentStatus.ESCALATED)
        incident.escalation_reason = result.reason

    await session.commit()
    await session.refresh(incident)
    return incident
