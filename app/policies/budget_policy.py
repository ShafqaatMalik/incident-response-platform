from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_spend import DailySpend
from app.policies.pricing_policy import calculate_cost


class BudgetExceededError(Exception):
    pass


def _today() -> date:
    return datetime.now(UTC).date()


def is_over_budget(current_spend: Decimal, daily_budget_limit_usd: float) -> bool:
    return current_spend >= Decimal(str(daily_budget_limit_usd))


async def is_budget_exceeded(session: AsyncSession, daily_budget_limit_usd: float) -> bool:
    result = await session.execute(
        select(DailySpend.total_cost_usd).where(DailySpend.date == _today())
    )
    current_spend = result.scalar_one_or_none() or Decimal("0")
    return is_over_budget(current_spend, daily_budget_limit_usd)


async def record_spend(
    session: AsyncSession, model: str, input_tokens: int, output_tokens: int
) -> None:
    cost = calculate_cost(model, input_tokens, output_tokens)
    stmt = insert(DailySpend).values(date=_today(), total_cost_usd=cost)
    stmt = stmt.on_conflict_do_update(
        index_elements=[DailySpend.date],
        set_={"total_cost_usd": DailySpend.total_cost_usd + cost},
    )
    await session.execute(stmt)
    await session.commit()
