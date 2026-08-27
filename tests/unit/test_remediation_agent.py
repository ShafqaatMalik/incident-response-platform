from unittest.mock import AsyncMock, patch

import anthropic
import pytest
from pydantic import ValidationError

from app.agents.remediation import RemediationFailedError, call_remediation_agent_with_retry
from app.models.schemas import RemediationContext, RemediationResult

CONTEXT = RemediationContext(
    trigger="Checkout API returning 500s",
    affected_service="checkout-api",
    root_cause="database connection pool exhaustion from a recent deploy",
    diagnosis_confidence="high",
    evidence=["connection pool at 0 available connections"],
)

RESULT = RemediationResult(
    action_type="restart_service",
    justification="connection pool exhaustion clears on restart",
    action_detail="restart checkout-api",
)


async def test_succeeds_on_first_call() -> None:
    with patch(
        "app.agents.remediation._request_remediation", AsyncMock(return_value=RESULT)
    ) as mock:
        result = await call_remediation_agent_with_retry(CONTEXT, "claude-sonnet-5")
    assert result is RESULT
    assert mock.await_count == 1


async def test_recovers_on_retry_after_validation_error() -> None:
    mock = AsyncMock(
        side_effect=[ValidationError.from_exception_data("RemediationResult", []), RESULT]
    )
    with patch("app.agents.remediation._request_remediation", mock):
        result = await call_remediation_agent_with_retry(CONTEXT, "claude-sonnet-5")
    assert result is RESULT
    assert mock.await_count == 2
    _, second_call_kwargs = mock.await_args_list[1]
    assert second_call_kwargs.get("repair_note")


async def test_recovers_on_retry_after_anthropic_error() -> None:
    api_error = anthropic.APIConnectionError(request=object())  # type: ignore[arg-type]
    mock = AsyncMock(side_effect=[api_error, RESULT])
    with patch("app.agents.remediation._request_remediation", mock):
        result = await call_remediation_agent_with_retry(CONTEXT, "claude-sonnet-5")
    assert result is RESULT
    assert mock.await_count == 2


async def test_escalates_after_second_failure() -> None:
    mock = AsyncMock(
        side_effect=[
            ValidationError.from_exception_data("RemediationResult", []),
            ValidationError.from_exception_data("RemediationResult", []),
        ]
    )
    with (
        patch("app.agents.remediation._request_remediation", mock),
        pytest.raises(RemediationFailedError),
    ):
        await call_remediation_agent_with_retry(CONTEXT, "claude-sonnet-5")
    assert mock.await_count == 2
