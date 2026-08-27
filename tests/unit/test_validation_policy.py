from app.models.incident import Incident
from app.policies.validation_policy import validate_remediation


def _incident(**overrides: object) -> Incident:
    defaults: dict[str, object] = {
        "trigger": "t",
        "evidence": ["500s in logs"],
        "status": "validating",
        "proposed_action_type": "restart_service",
        "action_justification": "justification",
        "action_detail": "detail",
        "action_risk_level": "medium",
        "deployment_correlation": None,
        "service_health_summary": None,
        "diagnosis_confidence": "high",
    }
    defaults.update(overrides)
    return Incident(**defaults)


# Rule 1: action_type must be one of the six fixed ActionType values


def test_rule1_passes_with_a_fixed_action_type() -> None:
    incident = _incident(proposed_action_type="restart_service")
    assert validate_remediation(incident).passed is True


def test_rule1_fails_with_an_invalid_action_type() -> None:
    incident = _incident(proposed_action_type="delete_everything")
    result = validate_remediation(incident)
    assert result.passed is False
    assert result.reason is not None
    assert "Rule 1" in result.reason


def test_rule1_fails_when_action_type_is_missing() -> None:
    incident = _incident(proposed_action_type=None)
    result = validate_remediation(incident)
    assert result.passed is False
    assert result.reason is not None
    assert "Rule 1" in result.reason


# Rule 2: action_justification, action_detail, action_risk_level all non-empty


def test_rule2_passes_when_all_three_fields_are_set() -> None:
    incident = _incident(action_justification="j", action_detail="d", action_risk_level="medium")
    assert validate_remediation(incident).passed is True


def test_rule2_fails_when_justification_is_missing() -> None:
    incident = _incident(action_justification=None)
    result = validate_remediation(incident)
    assert result.passed is False
    assert result.reason is not None
    assert "Rule 2" in result.reason


# Rule 3: rollback_deployment requires non-empty deployment_correlation


def test_rule3_passes_for_rollback_with_deployment_correlation_set() -> None:
    incident = _incident(
        proposed_action_type="rollback_deployment",
        deployment_correlation="deploy v1.42.0 8 min before onset",
    )
    assert validate_remediation(incident).passed is True


def test_rule3_fails_for_rollback_without_deployment_correlation() -> None:
    incident = _incident(proposed_action_type="rollback_deployment", deployment_correlation=None)
    result = validate_remediation(incident)
    assert result.passed is False
    assert result.reason is not None
    assert "Rule 3" in result.reason


# Rule 4: restart_service/disable_traffic require non-empty evidence


def test_rule4_passes_for_restart_service_with_evidence() -> None:
    incident = _incident(proposed_action_type="restart_service", evidence=["500s in logs"])
    assert validate_remediation(incident).passed is True


def test_rule4_fails_for_disable_traffic_without_evidence() -> None:
    incident = _incident(proposed_action_type="disable_traffic", evidence=[])
    result = validate_remediation(incident)
    assert result.passed is False
    assert result.reason is not None
    assert "Rule 4" in result.reason


# Rule 5: scale_up requires non-empty service_health_summary


def test_rule5_passes_for_scale_up_with_service_health_summary() -> None:
    incident = _incident(
        proposed_action_type="scale_up",
        service_health_summary="elevated CPU utilization",
    )
    assert validate_remediation(incident).passed is True


def test_rule5_fails_for_scale_up_without_service_health_summary() -> None:
    incident = _incident(proposed_action_type="scale_up", service_health_summary=None)
    result = validate_remediation(incident)
    assert result.passed is False
    assert result.reason is not None
    assert "Rule 5" in result.reason


# Rule 6: no_action_needed must not have diagnosis_confidence == "low"


def test_rule6_passes_for_no_action_needed_with_high_confidence() -> None:
    incident = _incident(proposed_action_type="no_action_needed", diagnosis_confidence="high")
    assert validate_remediation(incident).passed is True


def test_rule6_fails_for_no_action_needed_with_low_confidence() -> None:
    incident = _incident(proposed_action_type="no_action_needed", diagnosis_confidence="low")
    result = validate_remediation(incident)
    assert result.passed is False
    assert result.reason is not None
    assert "Rule 6" in result.reason


def test_manual_investigation_required_always_passes_rule_wise() -> None:
    # No rule beyond rule 2 applies to manual_investigation_required —
    # deliberately: a human reviews it regardless, and high confidence +
    # "needs manual investigation" is a legitimate combination.
    incident = _incident(
        proposed_action_type="manual_investigation_required",
        deployment_correlation=None,
        service_health_summary=None,
        evidence=[],
        diagnosis_confidence="low",
    )
    assert validate_remediation(incident).passed is True
