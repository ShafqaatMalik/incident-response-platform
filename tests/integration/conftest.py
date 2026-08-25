import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.db.base import Base
from app.models.document import Document


def _database_url() -> str:
    return os.environ["DATABASE_URL"]


@pytest_asyncio.fixture(scope="session")
async def engine() -> AsyncGenerator[AsyncEngine]:
    eng = create_async_engine(_database_url())
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _clean_documents(engine: AsyncEngine) -> AsyncGenerator[None]:
    yield
    async with engine.begin() as conn:
        await conn.execute(delete(Document))


@pytest_asyncio.fixture
async def client(engine: AsyncEngine) -> AsyncGenerator[AsyncClient]:
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
