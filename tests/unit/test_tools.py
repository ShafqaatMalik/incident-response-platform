import asyncio

from app.models.schemas import DeploymentEvent, LogEntry, ServiceMetrics
from app.tools.deployments import get_deployment_history
from app.tools.logs import get_recent_logs
from app.tools.metrics import get_service_metrics


async def test_get_recent_logs_returns_log_entries() -> None:
    logs = await get_recent_logs("checkout-api")
    assert logs
    assert all(isinstance(entry, LogEntry) for entry in logs)


async def test_get_recent_logs_respects_limit() -> None:
    logs = await get_recent_logs("checkout-api", limit=1)
    assert len(logs) == 1


async def test_get_recent_logs_is_deterministic_content() -> None:
    first = await get_recent_logs("checkout-api")
    second = await get_recent_logs("checkout-api")
    assert [entry.message for entry in first] == [entry.message for entry in second]


async def test_get_deployment_history_returns_deployment_events() -> None:
    deployments = await get_deployment_history("checkout-api")
    assert deployments
    assert all(isinstance(event, DeploymentEvent) for event in deployments)


async def test_get_deployment_history_respects_limit() -> None:
    deployments = await get_deployment_history("checkout-api", limit=1)
    assert len(deployments) == 1


async def test_get_service_metrics_returns_service_metrics() -> None:
    metrics = await get_service_metrics("checkout-api")
    assert isinstance(metrics, ServiceMetrics)
    assert metrics.error_rate > 0


# --- trigger-based variation ---


async def test_get_recent_logs_reflects_database_keyword() -> None:
    logs = await get_recent_logs("checkout-api", "the database is unreachable")
    assert any("connection pool" in entry.message for entry in logs)


async def test_get_deployment_history_reflects_deployment_keyword() -> None:
    deployments = await get_deployment_history("checkout-api", "a new deploy just rolled out")
    versions = {event.version for event in deployments}
    # both the scenario's own recent deploy and the always-present older one
    assert len(versions) == 2


async def test_get_deployment_history_has_no_recent_deploy_for_database_keyword() -> None:
    deployments = await get_deployment_history("checkout-api", "the database is unreachable")
    # only the always-present older entry -- nothing recent to correlate
    assert len(deployments) == 1


async def test_unmatched_trigger_still_returns_well_typed_non_empty_results() -> None:
    trigger = "a flock of geese landed on the runway"
    logs, deployments, metrics = await asyncio.gather(
        get_recent_logs("checkout-api", trigger),
        get_deployment_history("checkout-api", trigger),
        get_service_metrics("checkout-api", trigger),
    )
    assert logs and all(isinstance(entry, LogEntry) for entry in logs)
    assert deployments and all(isinstance(event, DeploymentEvent) for event in deployments)
    assert isinstance(metrics, ServiceMetrics)


async def test_all_three_stubs_agree_on_the_same_scenario_for_the_same_trigger() -> None:
    trigger = "certificate for the identity provider expired"
    logs, deployments, metrics = await asyncio.gather(
        get_recent_logs("checkout-api", trigger),
        get_deployment_history("checkout-api", trigger),
        get_service_metrics("checkout-api", trigger),
    )

    # auth-flavored log content...
    assert any("certificate" in entry.message.lower() for entry in logs)
    # ...no recent deploy to correlate (auth scenario has none)...
    assert len(deployments) == 1
    # ...and metrics matching fake_data.py's exact "auth" bucket values.
    assert metrics.error_rate == 0.15
    assert metrics.p99_latency_ms == 350.0
    assert metrics.cpu_utilization == 0.30
