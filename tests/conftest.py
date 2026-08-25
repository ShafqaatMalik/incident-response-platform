import os

os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/test")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "1000")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("ENVIRONMENT", "test")

import pytest


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"X-API-Key": os.environ["API_KEY"]}
