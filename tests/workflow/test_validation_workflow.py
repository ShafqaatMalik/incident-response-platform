import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import ActionType, Incident, IncidentStatus
from app.orchestration.validation_workflow import run_validation


def _validating_incident(**overrides: object) -> Incident:
    defaults: dict[str, object] = {
        "trigger": "Checkout API returning 500s",
        "evidence": ["500s in logs", "connection pool at 0 available connections"],
        "status": IncidentStatus.VALIDATING.value,
        "severity": "high",
        "affected_service": "checkout-api",
        "symptoms": ["elevated 500s"],
        "deployment_correlation": "deploy v1.42.0 8 min before onset",
        "service_health_summary": "elevated error rate and latency",
        "investigation_confidence": "high",
        "root_cause": "database connection pool exhaustion from a recent deploy",
        "diagnosis_confidence": "high",
        "proposed_action_type": "restart_service",
        "action_risk_level": "medium",
        "action_justification": "connection pool exhaustion clears on restart",
        "action_detail": "restart checkout-api",
    }
    defaults.update(overrides)
    return Incident(**defaults)


async def test_happy_path_transitions_validating_to_awaiting_approval(
    db_session: AsyncSession,
) -> None:
    incident = _validating_incident()
    db_session.add(incident)
    await db_session.commit()

    result = await run_validation(incident, db_session)

    assert result.status == IncidentStatus.AWAITING_APPROVAL.value
    assert result.escalation_reason is None


async def test_rule_failure_transitions_validating_to_escalated(
    db_session: AsyncSession,
) -> None:
    incident = _validating_incident(
        proposed_action_type="no_action_needed", diagnosis_confidence="low"
    )
    db_session.add(incident)
    await db_session.commit()

    result = await run_validation(incident, db_session)

    assert result.status == IncidentStatus.ESCALATED.value
    assert result.escalation_reason is not None
    assert "Rule 6" in result.escalation_reason


_PASSING_OVERRIDES: dict[ActionType, dict[str, object]] = {
    ActionType.RESTART_SERVICE: {"evidence": ["500s in logs"]},
    ActionType.ROLLBACK_DEPLOYMENT: {"deployment_correlation": "deploy v1.42.0"},
    ActionType.SCALE_UP: {"service_health_summary": "elevated CPU utilization"},
    ActionType.DISABLE_TRAFFIC: {"evidence": ["500s in logs"]},
    ActionType.NO_ACTION_NEEDED: {"diagnosis_confidence": "high"},
    ActionType.MANUAL_INVESTIGATION_REQUIRED: {},
}


@pytest.mark.parametrize("action_type", list(ActionType))
async def test_every_action_type_has_a_satisfiable_passing_case(
    db_session: AsyncSession, action_type: ActionType
) -> None:
    incident = _validating_incident(
        proposed_action_type=action_type.value, **_PASSING_OVERRIDES[action_type]
    )
    db_session.add(incident)
    await db_session.commit()

    result = await run_validation(incident, db_session)

    assert result.status == IncidentStatus.AWAITING_APPROVAL.value
