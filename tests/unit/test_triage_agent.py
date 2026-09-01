from unittest.mock import AsyncMock, patch

import anthropic
import pytest
from pydantic import ValidationError

from app.agents.triage import TriageFailedError, call_triage_agent_with_retry
from app.models.schemas import TriageContext, TriageResult

CONTEXT = TriageContext(trigger="Service returning 500s", initial_evidence=["500s in logs"])

RESULT = TriageResult(
    severity="high",
    affected_service="checkout-api",
    symptoms=["elevated 500s"],
    initial_evidence=["500s in logs"],
)


async def test_succeeds_on_first_call() -> None:
    with patch("app.agents.triage._request_triage", AsyncMock(return_value=RESULT)) as mock:
        result = await call_triage_agent_with_retry(CONTEXT, "claude-sonnet-5", None)
    assert result is RESULT
    assert mock.await_count == 1


async def test_recovers_on_retry_after_validation_error() -> None:
    mock = AsyncMock(side_effect=[ValidationError.from_exception_data("TriageResult", []), RESULT])
    with patch("app.agents.triage._request_triage", mock):
        result = await call_triage_agent_with_retry(CONTEXT, "claude-sonnet-5", None)
    assert result is RESULT
    assert mock.await_count == 2
    # the retry call passes a repair_note derived from the first failure
    _, second_call_kwargs = mock.await_args_list[1]
    assert second_call_kwargs.get("repair_note")


async def test_recovers_on_retry_after_anthropic_error() -> None:
    api_error = anthropic.APIConnectionError(request=object())  # type: ignore[arg-type]
    mock = AsyncMock(side_effect=[api_error, RESULT])
    with patch("app.agents.triage._request_triage", mock):
        result = await call_triage_agent_with_retry(CONTEXT, "claude-sonnet-5", None)
    assert result is RESULT
    assert mock.await_count == 2


async def test_escalates_after_second_failure() -> None:
    mock = AsyncMock(
        side_effect=[
            ValidationError.from_exception_data("TriageResult", []),
            ValidationError.from_exception_data("TriageResult", []),
        ]
    )
    with patch("app.agents.triage._request_triage", mock), pytest.raises(TriageFailedError):
        await call_triage_agent_with_retry(CONTEXT, "claude-sonnet-5", None)
    assert mock.await_count == 2
