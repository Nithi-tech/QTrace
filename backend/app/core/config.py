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

    # Public OSRM demo instance (CLAUDE.md #44 - no download/self-hosting required for
    # development). It is rate-limited and not for production load; point this at a
    # self-hosted OSRM server for production (CLAUDE.md #11, #34).
    osrm_base_url: str = Field(default="https://router.project-osrm.org")
    osrm_profile: str = Field(default="driving")

    geocoding_provider: str = Field(
        default="tomtom", description='"tomtom" (requires TOMTOM_API_KEY) or "nominatim" (keyless, OSM data).'
    )
    tomtom_api_key: str | None = Field(default=None)
    nominatim_base_url: str = Field(default="https://nominatim.openstreetmap.org")

    secret_key: str = Field(default="dev-secret-key-change-me")

    routing_request_timeout_seconds: float = Field(default=5.0)
    routing_max_retries: int = Field(default=2)

    # Bounds the coordinate count sent to OSRM's table service in one request
    # (CLAUDE.md #27 - do not assume unlimited provider capacity).
    max_route_stops: int = Field(default=25)


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance; avoids re-parsing env vars on every call."""
    return Settings()
