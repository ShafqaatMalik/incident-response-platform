from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.daily_spend import DailySpend
from app.policies.budget_policy import is_budget_exceeded, record_spend
from app.policies.pricing_policy import UnknownModelPricingError


async def test_empty_table_is_not_exceeded(db_session: AsyncSession) -> None:
    assert await is_budget_exceeded(db_session, 2.00) is False


async def test_seeded_row_at_limit_is_exceeded(db_session: AsyncSession) -> None:
    await record_spend(db_session, "claude-sonnet-5", input_tokens=1_000_000, output_tokens=0)
    # 1,000,000 input tokens at $2/MTok == exactly $2.00
    assert await is_budget_exceeded(db_session, 2.00) is True


async def test_record_spend_accumulates_across_calls(db_session: AsyncSession) -> None:
    await record_spend(db_session, "claude-sonnet-5", input_tokens=500_000, output_tokens=0)
    await record_spend(db_session, "claude-sonnet-5", input_tokens=500_000, output_tokens=0)

    result = await db_session.execute(select(DailySpend.total_cost_usd))
    total = result.scalar_one()
    assert total == Decimal("2.000000")


async def test_record_spend_unknown_model_raises(db_session: AsyncSession) -> None:
    with pytest.raises(UnknownModelPricingError):
        await record_spend(db_session, "not-a-real-model", input_tokens=100, output_tokens=100)
