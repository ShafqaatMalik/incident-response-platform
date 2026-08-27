"""Real-API evaluation tests. Costs money, never runs in CI — see testing.md.

Run explicitly: `uv run pytest tests/evaluation -m evaluation -v`
"""

import pytest

from app.agents.remediation import call_remediation_agent_with_retry
from app.models.schemas import RemediationContext

pytestmark = pytest.mark.evaluation


async def test_remediation_proposes_concrete_action_given_clear_diagnosis() -> None:
    context = RemediationContext(
        trigger="Checkout API returning 500s",
        affected_service="checkout-api",
        root_cause=(
            "database connection pool exhaustion caused by deploy v1.42.0, which reduced "
            "the configured pool size 8 minutes before symptom onset"
        ),
        diagnosis_confidence="high",
        evidence=[
            "connection pool at 0 available connections",
            "deploy v1.42.0 at 14:32 UTC reduced pool size",
            "error rate at 42%, p99 latency at 4200ms",
        ],
    )

    result = await call_remediation_agent_with_retry(context, "claude-sonnet-5")

    # Given a clear, well-evidenced root cause tied to a specific deploy,
    # the agent should propose a concrete action rather than punting to
    # manual review. Soft, non-brittle assertions — this checks the agent
    # reasons sensibly over the evidence, not an exact wording match.
    assert result.action_type.value != "manual_investigation_required"
    assert result.justification
    assert result.action_detail
