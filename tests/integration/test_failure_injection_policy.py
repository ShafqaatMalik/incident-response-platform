from sqlalchemy.ext.asyncio import AsyncSession

from app.policies.failure_injection_policy import is_injection_cap_exceeded, record_injection


async def test_empty_table_is_not_exceeded(db_session: AsyncSession) -> None:
    assert await is_injection_cap_exceeded(db_session, 5) is False


async def test_below_limit_is_not_exceeded(db_session: AsyncSession) -> None:
    for _ in range(4):
        await record_injection(db_session)

    assert await is_injection_cap_exceeded(db_session, 5) is False


async def test_at_limit_is_exceeded(db_session: AsyncSession) -> None:
    for _ in range(5):
        await record_injection(db_session)

    assert await is_injection_cap_exceeded(db_session, 5) is True
