from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.triage import TriageFailedError, build_triage_context, call_triage_agent_with_retry
from app.core.config import Settings
from app.models.incident import Incident, IncidentStatus
from app.orchestration.evidence import dedupe_evidence
from app.orchestration.state_machine import transition
from app.policies.budget_policy import BudgetExceededError, is_budget_exceeded


async def run_triage(incident: Incident, session: AsyncSession, settings: Settings) -> Incident:
    if await is_budget_exceeded(session, settings.daily_budget_limit_usd):
        raise BudgetExceededError("Daily AI budget exceeded.")

    context = build_triage_context(incident, settings)

    try:
        result = await call_triage_agent_with_retry(context, settings.triage_model, session)
    except TriageFailedError as exc:
        transition(incident, IncidentStatus.ESCALATED)
        incident.escalation_reason = str(exc)
    else:
        transition(incident, IncidentStatus.TRIAGED)
        incident.severity = result.severity.value
        incident.affected_service = result.affected_service
        incident.symptoms = result.symptoms
        incident.evidence = dedupe_evidence(list(incident.evidence or []) + result.initial_evidence)

    await session.commit()
    await session.refresh(incident)
    return incident
