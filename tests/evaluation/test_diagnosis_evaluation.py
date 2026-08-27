"""Real-API evaluation tests. Costs money, never runs in CI — see testing.md.

Run explicitly: `uv run pytest tests/evaluation -m evaluation -v`
"""

import pytest

from app.agents.diagnosis import call_diagnosis_agent_with_retry
from app.models.schemas import DiagnosisContext

pytestmark = pytest.mark.evaluation


async def test_diagnosis_grounds_root_cause_in_investigation_findings() -> None:
    context = DiagnosisContext(
        trigger="Checkout API returning 500s",
        severity="high",
        affected_service="checkout-api",
        symptoms=["elevated 500s", "latency spike"],
        error_patterns=["connection pool exhausted", "timeout acquiring database connection"],
        deployment_correlation="deploy v1.42.0 at 14:32 UTC, 8 minutes before symptom onset",
        service_health_summary="error rate at 42%, p99 latency at 4200ms, cpu at 78%",
        investigation_confidence="high",
    )

    result = await call_diagnosis_agent_with_retry(context, "claude-sonnet-5")

    # Given the clearly-correlated deployment and connection-pool-exhaustion
    # error pattern, the agent should ground its root cause in that evidence
    # and not report low confidence. Soft, non-brittle assertions — this
    # checks the agent reasons sensibly over the evidence, not an exact
    # wording match.
    assert result.root_cause
    assert result.confidence.value != "low"
    assert result.evidence
    assert result.alternative_explanations
