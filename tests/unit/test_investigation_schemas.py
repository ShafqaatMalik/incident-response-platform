from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models.schemas import (
    DeploymentEvent,
    InvestigationContext,
    InvestigationResult,
    LogEntry,
    ServiceMetrics,
)

SAMPLE_LOG = LogEntry(
    timestamp=datetime.now(UTC), level="ERROR", message="connection pool exhausted"
)
SAMPLE_DEPLOYMENT = DeploymentEvent(
    timestamp=datetime.now(UTC), version="v1.42.0", description="bump driver"
)
SAMPLE_METRICS = ServiceMetrics(error_rate=0.42, p99_latency_ms=4200.0, cpu_utilization=0.78)


def test_log_entry_requires_all_fields() -> None:
    with pytest.raises(ValidationError):
        LogEntry()  # type: ignore[call-arg]


def test_deployment_event_requires_all_fields() -> None:
    with pytest.raises(ValidationError):
        DeploymentEvent()  # type: ignore[call-arg]


def test_service_metrics_requires_all_fields() -> None:
    with pytest.raises(ValidationError):
        ServiceMetrics()  # type: ignore[call-arg]


def test_investigation_context_requires_all_fields() -> None:
    with pytest.raises(ValidationError):
        InvestigationContext()  # type: ignore[call-arg]


def test_investigation_context_accepts_valid_payload() -> None:
    context = InvestigationContext(
        trigger="Checkout API returning 500s",
        severity="high",
        affected_service="checkout-api",
        symptoms=["elevated 500s"],
        recent_logs=[SAMPLE_LOG],
        deployment_history=[SAMPLE_DEPLOYMENT],
        service_metrics=SAMPLE_METRICS,
    )
    assert context.affected_service == "checkout-api"
    assert context.recent_logs == [SAMPLE_LOG]


def test_investigation_result_rejects_empty_error_patterns() -> None:
    with pytest.raises(ValidationError):
        InvestigationResult(
            error_patterns=[],
            deployment_correlation="deployed 8 min before onset",
            service_health_summary="elevated error rate",
            confidence="high",
            evidence=["500s in logs"],
        )


def test_investigation_result_rejects_empty_deployment_correlation() -> None:
    with pytest.raises(ValidationError):
        InvestigationResult(
            error_patterns=["connection pool exhausted"],
            deployment_correlation="",
            service_health_summary="elevated error rate",
            confidence="high",
            evidence=["500s in logs"],
        )


def test_investigation_result_rejects_empty_service_health_summary() -> None:
    with pytest.raises(ValidationError):
        InvestigationResult(
            error_patterns=["connection pool exhausted"],
            deployment_correlation="deployed 8 min before onset",
            service_health_summary="",
            confidence="high",
            evidence=["500s in logs"],
        )


def test_investigation_result_rejects_empty_evidence() -> None:
    with pytest.raises(ValidationError):
        InvestigationResult(
            error_patterns=["connection pool exhausted"],
            deployment_correlation="deployed 8 min before onset",
            service_health_summary="elevated error rate",
            confidence="high",
            evidence=[],
        )


def test_investigation_result_rejects_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        InvestigationResult(
            error_patterns=["connection pool exhausted"],
            deployment_correlation="deployed 8 min before onset",
            service_health_summary="elevated error rate",
            confidence="extremely-sure",
            evidence=["500s in logs"],
        )


def test_investigation_result_accepts_valid_payload() -> None:
    result = InvestigationResult(
        error_patterns=["connection pool exhausted"],
        deployment_correlation="deployed 8 min before onset",
        service_health_summary="elevated error rate and latency",
        confidence="high",
        evidence=["500s in logs", "deploy v1.42.0 at 14:32 UTC"],
    )
    assert result.confidence.value == "high"
    assert result.error_patterns == ["connection pool exhausted"]
