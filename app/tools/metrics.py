"""STUB — no real metrics backend exists yet. Replace with a real Cloud
Monitoring integration in Build Order step 5 (ARCHITECTURE.md §20).
Returns deterministic fake metrics, correlated with app/tools/logs.py's
and app/tools/deployments.py's fake data, so the Investigation Agent has
something coherent to reason about.
"""

from app.models.schemas import ServiceMetrics


async def get_service_metrics(service: str) -> ServiceMetrics:
    return ServiceMetrics(error_rate=0.42, p99_latency_ms=4200.0, cpu_utilization=0.78)
