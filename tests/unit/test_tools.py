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
