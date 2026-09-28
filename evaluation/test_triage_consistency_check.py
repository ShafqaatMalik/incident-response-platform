import pytest
from triage_consistency_check import _ensure_local_database


def test_accepts_localhost() -> None:
    _ensure_local_database("postgresql+asyncpg://postgres:postgres@localhost:5432/test")


def test_accepts_127_0_0_1() -> None:
    _ensure_local_database("postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/test")


def test_refuses_a_supabase_style_url() -> None:
    with pytest.raises(SystemExit):
        _ensure_local_database(
            "postgresql+asyncpg://postgres.abc123:pw@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres"
        )
