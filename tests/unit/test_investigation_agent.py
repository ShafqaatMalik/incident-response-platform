from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import anthropic
import pytest
from pydantic import ValidationError

from app.agents.investigation import InvestigationFailedError, call_investigation_agent_with_retry
from app.models.schemas import (
    DeploymentEvent,
    InvestigationContext,
    InvestigationResult,
    LogEntry,
    ServiceMetrics,
)

CONTEXT = InvestigationContext(
    trigger="Checkout API returning 500s",
    severity="high",
    affected_service="checkout-api",
    symptoms=["elevated 500s"],
    recent_logs=[LogEntry(timestamp=datetime.now(UTC), level="ERROR", message="pool exhausted")],
    deployment_history=[
        DeploymentEvent(timestamp=datetime.now(UTC), version="v1.42.0", description="bump driver")
    ],
    service_metrics=ServiceMetrics(error_rate=0.42, p99_latency_ms=4200.0, cpu_utilization=0.78),
)

RESULT = InvestigationResult(
    error_patterns=["connection pool exhausted"],
    deployment_correlation="deployed 8 min before onset",
    service_health_summary="elevated error rate and latency",
    confidence="high",
    evidence=["500s in logs", "deploy v1.42.0"],
)


async def test_succeeds_on_first_call() -> None:
    with patch(
        "app.agents.investigation._request_investigation", AsyncMock(return_value=RESULT)
    ) as mock:
        result = await call_investigation_agent_with_retry(CONTEXT, "claude-sonnet-5", None)
    assert result is RESULT
    assert mock.await_count == 1


async def test_recovers_on_retry_after_validation_error() -> None:
    mock = AsyncMock(
        side_effect=[ValidationError.from_exception_data("InvestigationResult", []), RESULT]
    )
    with patch("app.agents.investigation._request_investigation", mock):
        result = await call_investigation_agent_with_retry(CONTEXT, "claude-sonnet-5", None)
    assert result is RESULT
    assert mock.await_count == 2
    _, second_call_kwargs = mock.await_args_list[1]
    assert second_call_kwargs.get("repair_note")


async def test_recovers_on_retry_after_anthropic_error() -> None:
    api_error = anthropic.APIConnectionError(request=object())  # type: ignore[arg-type]
    mock = AsyncMock(side_effect=[api_error, RESULT])
    with patch("app.agents.investigation._request_investigation", mock):
        result = await call_investigation_agent_with_retry(CONTEXT, "claude-sonnet-5", None)
    assert result is RESULT
    assert mock.await_count == 2


async def test_escalates_after_second_failure() -> None:
    mock = AsyncMock(
        side_effect=[
            ValidationError.from_exception_data("InvestigationResult", []),
            ValidationError.from_exception_data("InvestigationResult", []),
        ]
    )
    with (
        patch("app.agents.investigation._request_investigation", mock),
        pytest.raises(InvestigationFailedError),
    ):
        await call_investigation_agent_with_retry(CONTEXT, "claude-sonnet-5", None)
    assert mock.await_count == 2
