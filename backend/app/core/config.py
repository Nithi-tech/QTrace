"""Environment-driven application configuration (CLAUDE.md #18).

All environment-specific values (URLs, timeouts, secrets) must come from
environment variables, never be hard-coded (CLAUDE.md #35).
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "QTrace API"
    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(default="postgresql+psycopg://localhost/qtrace")
    redis_url: str = Field(default="redis://localhost:6379/0")

    osrm_base_url: str = Field(default="http://localhost:5000")
    tomtom_api_key: str | None = Field(default=None)

    secret_key: str = Field(default="dev-secret-key-change-me")

    routing_request_timeout_seconds: float = Field(default=5.0)
    routing_max_retries: int = Field(default=2)


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance; avoids re-parsing env vars on every call."""
    return Settings()
