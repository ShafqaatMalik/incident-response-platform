from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from judge import JudgeVerdict, call_judge_with_retry
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from scenarios import ExpectedOutcome, Scenario

from app.models.incident import Incident, IncidentStatus

FAKE_VERDICT = JudgeVerdict(
    severity_verdict="correct",
    severity_reasoning="matches",
    diagnosis_verdict="correct",
    diagnosis_reasoning="matches",
    remediation_verdict="not_applicable",
    remediation_reasoning="no remediation reached",
    hallucination_detected=False,
    hallucination_reasoning="grounded",
)


def _fake_client_response(input_tokens: int, output_tokens: int) -> Mock:
    response = SimpleNamespace(
        parsed_output=FAKE_VERDICT,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )
    fake_client = Mock()
    fake_client.messages.parse = AsyncMock(return_value=response)
    return fake_client


async def test_judge_span_carries_real_token_usage_attributes(
    span_exporter: InMemorySpanExporter,
) -> None:
    scenario = Scenario(
        id="s1",
        category="api_failure",
        trigger="t",
        expected=ExpectedOutcome(severity="high", should_escalate=False),
    )
    incident = Incident(trigger="t", evidence=[], status=IncidentStatus.ESCALATED.value)
    fake_client = _fake_client_response(input_tokens=1234, output_tokens=567)

    with patch("judge.get_anthropic_client", return_value=fake_client):
        verdict, error = await call_judge_with_retry(scenario, incident, "claude-sonnet-5")

    assert error is None
    assert verdict == FAKE_VERDICT

    spans = [s for s in span_exporter.get_finished_spans() if s.name == "judge.anthropic_call"]
    assert len(spans) == 1
    attributes = spans[0].attributes
    assert attributes is not None
    assert attributes["gen_ai.request.model"] == "claude-sonnet-5"
    assert attributes["gen_ai.usage.input_tokens"] == 1234
    assert attributes["gen_ai.usage.output_tokens"] == 567
