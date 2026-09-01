import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.investigation import (
    InvestigationFailedError,
    build_investigation_context,
    call_investigation_agent_with_retry,
)
from app.core.config import Settings
from app.models.incident import Incident, IncidentStatus, Severity
from app.orchestration.evidence import dedupe_evidence
from app.orchestration.state_machine import transition, validate_transition
from app.policies.budget_policy import BudgetExceededError, is_budget_exceeded
from app.tools.deployments import get_deployment_history
from app.tools.logs import get_recent_logs
from app.tools.metrics import get_service_metrics


async def run_investigation(
    incident: Incident, session: AsyncSession, settings: Settings
) -> Incident:
    if await is_budget_exceeded(session, settings.daily_budget_limit_usd):
        raise BudgetExceededError("Daily AI budget exceeded.")

    # Guard before touching any Triage-output field or calling tools/the agent:
    # unlike Triage (whose inputs are non-nullable columns present regardless of
    # status), Investigation's context depends on fields that are only
    # guaranteed non-null once status == TRIAGED. Checking this first — rather
    # than letting a bad call crash while reading those fields — is what turns
    # an out-of-order call into a clean 409 instead of an unhandled 500.
    validate_transition(incident, IncidentStatus.INVESTIGATING)
    assert incident.severity is not None, "TRIAGED invariant: severity is set"
    assert incident.affected_service is not None, "TRIAGED invariant: affected_service is set"
    severity = Severity(incident.severity)
    affected_service = incident.affected_service

    logs, deployments, metrics = await asyncio.gather(
        get_recent_logs(affected_service),
        get_deployment_history(affected_service),
        get_service_metrics(affected_service),
    )
    context = build_investigation_context(
        incident, severity, affected_service, logs, deployments, metrics
    )

    try:
        result = await call_investigation_agent_with_retry(
            context, settings.investigation_model, session
        )
    except InvestigationFailedError as exc:
        transition(incident, IncidentStatus.ESCALATED)
        incident.escalation_reason = str(exc)
    else:
        transition(incident, IncidentStatus.INVESTIGATING)
        incident.error_patterns = result.error_patterns
        incident.deployment_correlation = result.deployment_correlation
        incident.service_health_summary = result.service_health_summary
        incident.investigation_confidence = result.confidence.value
        incident.evidence = dedupe_evidence(list(incident.evidence or []) + result.evidence)

    await session.commit()
    await session.refresh(incident)
    return incident
