from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.triage import TriageFailedError, build_triage_context, call_triage_agent_with_retry
from app.core.config import Settings
from app.models.incident import Incident, IncidentStatus
from app.orchestration.state_machine import transition


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


async def run_triage(incident: Incident, session: AsyncSession, settings: Settings) -> Incident:
    context = build_triage_context(incident, settings)

    try:
        result = await call_triage_agent_with_retry(context, settings.triage_model)
    except TriageFailedError as exc:
        transition(incident, IncidentStatus.ESCALATED)
        incident.escalation_reason = str(exc)
    else:
        transition(incident, IncidentStatus.TRIAGED)
        incident.severity = result.severity.value
        incident.affected_service = result.affected_service
        incident.symptoms = result.symptoms
        incident.evidence = _dedupe(list(incident.evidence or []) + result.initial_evidence)

    await session.commit()
    await session.refresh(incident)
    return incident
