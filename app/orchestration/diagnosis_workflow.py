from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.diagnosis import (
    DiagnosisFailedError,
    build_diagnosis_context,
    call_diagnosis_agent_with_retry,
)
from app.core.config import Settings
from app.models.incident import Confidence, Incident, IncidentStatus, Severity
from app.orchestration.evidence import dedupe_evidence
from app.orchestration.state_machine import transition, validate_transition
from app.policies.budget_policy import BudgetExceededError, is_budget_exceeded


async def run_diagnosis(incident: Incident, session: AsyncSession, settings: Settings) -> Incident:
    if await is_budget_exceeded(session, settings.daily_budget_limit_usd):
        raise BudgetExceededError("Daily AI budget exceeded.")

    # Guard before touching any Triage/Investigation-output field: those
    # columns are only guaranteed non-null once status == INVESTIGATING.
    # Checking this first — rather than letting a bad call crash while
    # reading those fields — is what turns an out-of-order call into a
    # clean 409 instead of an unhandled 500.
    validate_transition(incident, IncidentStatus.DIAGNOSED)
    assert incident.severity is not None, "TRIAGED invariant: severity is set"
    assert incident.affected_service is not None, "TRIAGED invariant: affected_service is set"
    assert incident.deployment_correlation is not None, (
        "INVESTIGATING invariant: deployment_correlation is set"
    )
    assert incident.service_health_summary is not None, (
        "INVESTIGATING invariant: service_health_summary is set"
    )
    assert incident.investigation_confidence is not None, (
        "INVESTIGATING invariant: investigation_confidence is set"
    )
    severity = Severity(incident.severity)
    affected_service = incident.affected_service
    deployment_correlation = incident.deployment_correlation
    service_health_summary = incident.service_health_summary
    investigation_confidence = Confidence(incident.investigation_confidence)

    context = build_diagnosis_context(
        incident,
        severity,
        affected_service,
        deployment_correlation,
        service_health_summary,
        investigation_confidence,
    )

    try:
        result = await call_diagnosis_agent_with_retry(context, settings.diagnosis_model, session)
    except DiagnosisFailedError as exc:
        transition(incident, IncidentStatus.ESCALATED)
        incident.escalation_reason = str(exc)
    else:
        transition(incident, IncidentStatus.DIAGNOSED)
        incident.root_cause = result.root_cause
        incident.alternative_explanations = result.alternative_explanations
        incident.diagnosis_confidence = result.confidence.value
        incident.evidence = dedupe_evidence(list(incident.evidence or []) + result.evidence)

    await session.commit()
    await session.refresh(incident)
    return incident
