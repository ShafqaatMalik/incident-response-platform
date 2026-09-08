"""STUB — no real metrics backend exists yet. Replace with a real Cloud
Monitoring integration in Build Order step 5 (ARCHITECTURE.md §20).
Returns deterministic fake metrics, keyword-matched against the
incident's trigger text via app/tools/fake_data.py so the returned
story actually relates to what the incident describes, instead of
always being the same fixed values.
"""

from app.models.schemas import ServiceMetrics
from app.tools.fake_data import select_scenario


async def get_service_metrics(service: str, trigger: str = "") -> ServiceMetrics:
    scenario = select_scenario(trigger)
    return ServiceMetrics(
        error_rate=scenario.error_rate,
        p99_latency_ms=scenario.p99_latency_ms,
        cpu_utilization=scenario.cpu_utilization,
    )
