"""Real-API evaluation tests. Costs money, never runs in CI — see testing.md.

Run explicitly: `uv run pytest tests/evaluation -m evaluation -v`
"""

import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.investigation import (
    build_investigation_context,
    call_investigation_agent_with_retry,
)
from app.models.incident import Incident, Severity
from app.tools.deployments import get_deployment_history
from app.tools.logs import get_recent_logs
from app.tools.metrics import get_service_metrics

pytestmark = pytest.mark.evaluation


async def test_investigation_correlates_stub_deployment_with_symptoms(
    db_session: AsyncSession,
) -> None:
    incident = Incident(
        trigger="Checkout API returning 500s immediately following today's deployment",
        evidence=["500s in logs"],
        status="triaged",
        severity="high",
        affected_service="checkout-api",
        symptoms=["elevated 500s", "latency spike"],
    )

    logs, deployments, metrics = await asyncio.gather(
        get_recent_logs(incident.affected_service, incident.trigger),
        get_deployment_history(incident.affected_service, incident.trigger),
        get_service_metrics(incident.affected_service, incident.trigger),
    )
    context = build_investigation_context(
        incident, Severity(incident.severity), incident.affected_service, logs, deployments, metrics
    )

    result = await call_investigation_agent_with_retry(context, "claude-sonnet-5", db_session)

    # The trigger's "deployment" keyword selects app/tools/fake_data.py's
    # "deployment" scenario -- a recent deploy (~8 min before "now") paired
    # with matching failing-health-check error logs and an elevated error
    # rate -- so the agent should not dismiss the correlation or report low
    # confidence. Soft, non-brittle assertions -- this checks the agent
    # reasons sensibly over the evidence, not an exact wording match.
    assert result.error_patterns
    assert result.deployment_correlation
    assert "no correlated deployment" not in result.deployment_correlation.lower()
    assert result.confidence.value != "low"
    assert result.evidence
