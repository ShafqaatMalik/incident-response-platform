from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    api_key: str
    database_url: str
    rate_limit_per_minute: int = 60
    log_level: str = "INFO"
    environment: str = "development"
    triage_model: str = "claude-sonnet-5"
    investigation_model: str = "claude-sonnet-5"
    diagnosis_model: str = "claude-sonnet-5"
    remediation_model: str = "claude-sonnet-5"
    daily_budget_limit_usd: float = 2.00


@lru_cache
def get_settings() -> Settings:
    return Settings()
