"""Real-API evaluation tests. Costs money, never runs in CI — see testing.md.

Run explicitly: `uv run pytest tests/evaluation -m evaluation -v`
"""

import pytest

from app.agents.triage import call_triage_agent_with_retry
from app.models.schemas import TriageContext

pytestmark = pytest.mark.evaluation


async def test_severe_trigger_is_not_triaged_as_low_severity() -> None:
    context = TriageContext(
        trigger=(
            "Total outage: checkout-api is returning 100% 5xx errors across all regions, "
            "database connection pool exhausted, customers cannot complete purchases."
        ),
        initial_evidence=[
            "checkout-api error rate at 100% for the last 12 minutes",
            "database connection pool at 0 available connections",
        ],
        service_metadata={"service_name": "checkout-api", "environment": "production"},
    )

    result = await call_triage_agent_with_retry(context, "claude-sonnet-5")

    assert result.severity.value != "low"
    assert result.affected_service
    assert len(result.symptoms) >= 1
    assert len(result.initial_evidence) >= 1
