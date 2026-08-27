from unittest.mock import AsyncMock, patch

import anthropic
import pytest
from pydantic import ValidationError

from app.agents.diagnosis import DiagnosisFailedError, call_diagnosis_agent_with_retry
from app.models.schemas import DiagnosisContext, DiagnosisResult

CONTEXT = DiagnosisContext(
    trigger="Checkout API returning 500s",
    severity="high",
    affected_service="checkout-api",
    symptoms=["elevated 500s"],
    error_patterns=["connection pool exhausted"],
    deployment_correlation="deployed 8 min before onset",
    service_health_summary="elevated error rate and latency",
    investigation_confidence="high",
)

RESULT = DiagnosisResult(
    root_cause="database connection pool exhaustion from a recent deploy",
    evidence=["connection pool exhausted", "deploy v1.42.0"],
    confidence="high",
    alternative_explanations=["no plausible alternative explanations found"],
)


async def test_succeeds_on_first_call() -> None:
    with patch("app.agents.diagnosis._request_diagnosis", AsyncMock(return_value=RESULT)) as mock:
        result = await call_diagnosis_agent_with_retry(CONTEXT, "claude-sonnet-5")
    assert result is RESULT
    assert mock.await_count == 1


async def test_recovers_on_retry_after_validation_error() -> None:
    mock = AsyncMock(
        side_effect=[ValidationError.from_exception_data("DiagnosisResult", []), RESULT]
    )
    with patch("app.agents.diagnosis._request_diagnosis", mock):
        result = await call_diagnosis_agent_with_retry(CONTEXT, "claude-sonnet-5")
    assert result is RESULT
    assert mock.await_count == 2
    _, second_call_kwargs = mock.await_args_list[1]
    assert second_call_kwargs.get("repair_note")


async def test_recovers_on_retry_after_anthropic_error() -> None:
    api_error = anthropic.APIConnectionError(request=object())  # type: ignore[arg-type]
    mock = AsyncMock(side_effect=[api_error, RESULT])
    with patch("app.agents.diagnosis._request_diagnosis", mock):
        result = await call_diagnosis_agent_with_retry(CONTEXT, "claude-sonnet-5")
    assert result is RESULT
    assert mock.await_count == 2


async def test_escalates_after_second_failure() -> None:
    mock = AsyncMock(
        side_effect=[
            ValidationError.from_exception_data("DiagnosisResult", []),
            ValidationError.from_exception_data("DiagnosisResult", []),
        ]
    )
    with (
        patch("app.agents.diagnosis._request_diagnosis", mock),
        pytest.raises(DiagnosisFailedError),
    ):
        await call_diagnosis_agent_with_retry(CONTEXT, "claude-sonnet-5")
    assert mock.await_count == 2
