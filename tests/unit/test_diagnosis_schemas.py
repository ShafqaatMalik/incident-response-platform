import pytest
from pydantic import ValidationError

from app.models.schemas import DiagnosisContext, DiagnosisResult


def test_diagnosis_context_requires_all_fields() -> None:
    with pytest.raises(ValidationError):
        DiagnosisContext()  # type: ignore[call-arg]


def test_diagnosis_context_accepts_valid_payload() -> None:
    context = DiagnosisContext(
        trigger="Checkout API returning 500s",
        severity="high",
        affected_service="checkout-api",
        symptoms=["elevated 500s"],
        error_patterns=["connection pool exhausted"],
        deployment_correlation="deployed 8 min before onset",
        service_health_summary="elevated error rate and latency",
        investigation_confidence="high",
    )
    assert context.affected_service == "checkout-api"
    assert context.deployment_correlation == "deployed 8 min before onset"


def test_diagnosis_result_rejects_empty_root_cause() -> None:
    with pytest.raises(ValidationError):
        DiagnosisResult(
            root_cause="",
            evidence=["connection pool exhausted"],
            confidence="high",
            alternative_explanations=["no plausible alternative explanations found"],
        )


def test_diagnosis_result_rejects_empty_evidence() -> None:
    with pytest.raises(ValidationError):
        DiagnosisResult(
            root_cause="database connection pool exhaustion from a recent deploy",
            evidence=[],
            confidence="high",
            alternative_explanations=["no plausible alternative explanations found"],
        )


def test_diagnosis_result_rejects_empty_alternative_explanations() -> None:
    with pytest.raises(ValidationError):
        DiagnosisResult(
            root_cause="database connection pool exhaustion from a recent deploy",
            evidence=["connection pool exhausted"],
            confidence="high",
            alternative_explanations=[],
        )


def test_diagnosis_result_rejects_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        DiagnosisResult(
            root_cause="database connection pool exhaustion from a recent deploy",
            evidence=["connection pool exhausted"],
            confidence="extremely-sure",
            alternative_explanations=["no plausible alternative explanations found"],
        )


def test_diagnosis_result_accepts_valid_payload() -> None:
    result = DiagnosisResult(
        root_cause="database connection pool exhaustion from a recent deploy",
        evidence=["connection pool exhausted", "deploy v1.42.0 at 14:32 UTC"],
        confidence="high",
        alternative_explanations=["no plausible alternative explanations found"],
    )
    assert result.confidence.value == "high"
    assert result.root_cause == "database connection pool exhaustion from a recent deploy"
