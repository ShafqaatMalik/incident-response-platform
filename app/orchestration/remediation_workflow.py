from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.remediation import (
    RemediationFailedError,
    build_remediation_context,
    call_remediation_agent_with_retry,
)
from app.core.config import Settings
from app.models.incident import Confidence, Incident, IncidentStatus
from app.orchestration.state_machine import transition, validate_transition
from app.policies.remediation_policy import risk_level_for


async def run_remediation(
    incident: Incident, session: AsyncSession, settings: Settings
) -> Incident:
    # Guard before touching any Triage/Diagnosis-output field: root_cause
    # and diagnosis_confidence are only guaranteed non-null once
    # status == DIAGNOSED. Checking this first — rather than letting a bad
    # call crash while reading those fields — is what turns an out-of-order
    # call into a clean 409 instead of an unhandled 500.
    validate_transition(incident, IncidentStatus.VALIDATING)
    assert incident.affected_service is not None, "TRIAGED invariant: affected_service is set"
    assert incident.root_cause is not None, "DIAGNOSED invariant: root_cause is set"
    assert incident.diagnosis_confidence is not None, (
        "DIAGNOSED invariant: diagnosis_confidence is set"
    )
    affected_service = incident.affected_service
    root_cause = incident.root_cause
    diagnosis_confidence = Confidence(incident.diagnosis_confidence)

    context = build_remediation_context(
        incident, affected_service, root_cause, diagnosis_confidence
    )

    try:
        result = await call_remediation_agent_with_retry(context, settings.remediation_model)
    except RemediationFailedError as exc:
        transition(incident, IncidentStatus.ESCALATED)
        incident.escalation_reason = str(exc)
    else:
        transition(incident, IncidentStatus.VALIDATING)
        incident.proposed_action_type = result.action_type.value
        incident.action_risk_level = risk_level_for(result.action_type).value
        incident.action_justification = result.justification
        incident.action_detail = result.action_detail

    await session.commit()
    await session.refresh(incident)
    return incident
