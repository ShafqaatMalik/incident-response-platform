from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from harness import run_scenario
from judge import JudgeVerdict
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from scenarios import ExpectedOutcome, Scenario
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
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


async def _fake_run_triage(incident: Incident, session: AsyncSession, settings: object) -> Incident:
    # Simplest possible pipeline exit: escalate immediately. The ordering bug
    # this test guards against doesn't depend on how far the pipeline gets --
    # call_judge_with_retry runs unconditionally after the try block either
    # way, so this is enough to exercise it without mocking all 5 stages.
    incident.status = IncidentStatus.ESCALATED.value
    incident.escalation_reason = "test-only escalation"
    await session.commit()
    await session.refresh(incident)
    return incident


async def test_judge_cost_is_captured_after_a_full_run_scenario_call(
    db_session: AsyncSession, span_exporter: InMemorySpanExporter
) -> None:
    """Regression test for the call-ordering bug: run_scenario() used to read
    spans (extract_call_records) and freeze judge_cost_usd into
    RuleBasedResult *before* call_judge_with_retry ever ran, so the judge's
    own span never existed yet and judge_cost_usd was always 0 -- even
    though judge.py itself correctly set usage attributes on it. This
    exercises the real run_scenario() function end to end (not checks.py's
    cost arithmetic or judge.py's span-attribute logic in isolation) to
    prove the fix actually wires the two together in the right order."""
    scenario = Scenario(
        id="s1",
        category="api_failure",
        trigger="t",
        expected=ExpectedOutcome(severity="high", should_escalate=True),
    )

    response = SimpleNamespace(
        parsed_output=FAKE_VERDICT,
        usage=SimpleNamespace(input_tokens=999, output_tokens=111),
    )
    fake_client = Mock()
    fake_client.messages.parse = AsyncMock(return_value=response)

    with (
        patch("harness.run_triage", _fake_run_triage),
        patch("judge.get_anthropic_client", return_value=fake_client),
    ):
        result = await run_scenario(scenario, db_session, get_settings(), span_exporter)

    assert result.judge == FAKE_VERDICT
    assert result.rule_based is not None
    assert result.rule_based.judge_cost_usd > 0
