import pytest
from pydantic import ValidationError

from app.models.schemas import RemediationContext, RemediationResult


def test_remediation_context_requires_all_fields() -> None:
    with pytest.raises(ValidationError):
        RemediationContext()  # type: ignore[call-arg]


def test_remediation_context_accepts_valid_payload() -> None:
    context = RemediationContext(
        trigger="Checkout API returning 500s",
        affected_service="checkout-api",
        root_cause="database connection pool exhaustion from a recent deploy",
        diagnosis_confidence="high",
        evidence=["connection pool at 0 available connections"],
    )
    assert context.affected_service == "checkout-api"
    assert context.diagnosis_confidence.value == "high"


def test_remediation_result_rejects_invalid_action_type() -> None:
    with pytest.raises(ValidationError):
        RemediationResult(
            action_type="delete_database",
            justification="this is not a real action type",
            action_detail="checkout-api",
        )


def test_remediation_result_rejects_empty_justification() -> None:
    with pytest.raises(ValidationError):
        RemediationResult(
            action_type="restart_service",
            justification="",
            action_detail="restart checkout-api",
        )


def test_remediation_result_rejects_empty_action_detail() -> None:
    with pytest.raises(ValidationError):
        RemediationResult(
            action_type="restart_service",
            justification="connection pool exhaustion clears on restart",
            action_detail="",
        )


def test_remediation_result_accepts_valid_payload() -> None:
    result = RemediationResult(
        action_type="restart_service",
        justification="connection pool exhaustion clears on restart",
        action_detail="restart checkout-api",
    )
    assert result.action_type.value == "restart_service"
    assert result.action_detail == "restart checkout-api"
