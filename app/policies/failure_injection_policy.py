from datetime import UTC, date, datetime
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_injection import DailyInjection


class InjectionCapExceededError(Exception):
    pass


class FailureCategory(StrEnum):
    DEPENDENCY_TIMEOUT = "dependency_timeout"
    ELEVATED_ERROR_RATE = "elevated_error_rate"
    LATENCY_SPIKE = "latency_spike"


_TRIGGERS: dict[FailureCategory, tuple[str, list[str]]] = {
    FailureCategory.DEPENDENCY_TIMEOUT: (
        "Database queries to the primary Postgres instance are timing out "
        "after 30s; multiple endpoints are returning 504 Gateway Timeout.",
        [
            "connection pool exhausted",
            "query timeout after 30000ms",
            "db.primary.internal unreachable from 3 of 4 app instances",
        ],
    ),
    FailureCategory.ELEVATED_ERROR_RATE: (
        "checkout-api is returning HTTP 500 for roughly 18% of requests "
        "over the last 10 minutes, up from a baseline under 1%.",
        [
            "error rate spike detected at 14:32 UTC",
            "500 Internal Server Error on POST /checkout",
            "affected requests concentrated on the payment-processing code path",
        ],
    ),
    FailureCategory.LATENCY_SPIKE: (
        "p99 latency on the /documents endpoint has climbed to 4.2s, "
        "roughly 6x the 700ms baseline, with no accompanying error rate increase.",
        [
            "p99 latency 4200ms vs 700ms baseline",
            "no increase in 4xx/5xx error rate",
            "CPU utilization on app instances elevated to 85%",
        ],
    ),
}


def build_injection_trigger(category: FailureCategory) -> tuple[str, list[str]]:
    return _TRIGGERS[category]


def _today() -> date:
    return datetime.now(UTC).date()


def is_over_cap(current_count: int, daily_limit: int) -> bool:
    return current_count >= daily_limit


async def is_injection_cap_exceeded(session: AsyncSession, daily_limit: int) -> bool:
    result = await session.execute(
        select(DailyInjection.count).where(DailyInjection.date == _today())
    )
    current_count = result.scalar_one_or_none() or 0
    return is_over_cap(current_count, daily_limit)


async def record_injection(session: AsyncSession) -> None:
    stmt = insert(DailyInjection).values(date=_today(), count=1)
    stmt = stmt.on_conflict_do_update(
        index_elements=[DailyInjection.date], set_={"count": DailyInjection.count + 1}
    )
    await session.execute(stmt)
