import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.core.security import require_api_key


def _settings() -> Settings:
    return Settings(api_key="correct-key", database_url="postgresql+asyncpg://u:p@h/d")


def test_accepts_correct_key() -> None:
    require_api_key(provided_key="correct-key", settings=_settings())


def test_rejects_missing_key() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_api_key(provided_key=None, settings=_settings())
    assert exc_info.value.status_code == 401


def test_rejects_wrong_key() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_api_key(provided_key="wrong", settings=_settings())
    assert exc_info.value.status_code == 401
