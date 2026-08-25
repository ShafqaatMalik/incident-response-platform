from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    api_key: str
    database_url: str
    rate_limit_per_minute: int = 60
    log_level: str = "INFO"
    environment: str = "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
