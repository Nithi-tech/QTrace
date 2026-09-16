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

    # QTrace crowd-traffic telemetry (docs/TRAFFIC_ARCHITECTURE.md). No commercial
    # traffic API is used - this is QTrace's own anonymized GPS telemetry, map-matched
    # against OSRM. traffic_enabled gates whether the optimizer consumes it at all;
    # traffic_telemetry_ingestion_enabled separately gates whether the ingestion
    # endpoint accepts new observations (so optimization can keep using a
    # previously-built baseline even if ingestion is paused).
    traffic_enabled: bool = Field(default=True)
    traffic_telemetry_ingestion_enabled: bool = Field(default=True)

    # Freshness thresholds (CLAUDE.md traffic-free-system master-prompt #17).
    traffic_live_ttl_seconds: float = Field(default=120.0)
    traffic_recent_ttl_seconds: float = Field(default=300.0)
    traffic_expired_seconds: float = Field(default=900.0)

    # A segment's current snapshot is not trusted until at least this many independent
    # observations back it (CLAUDE.md traffic-free-system master-prompt #16).
    traffic_min_observations: int = Field(default=3)

    # Corridor width used to match stop-pairs to nearby segments at optimization time
    # (same role as OSRM_TABLE/HERE corridor matching in the routing docs).
    traffic_corridor_radius_meters: float = Field(default=100.0)

    # Retention (CLAUDE.md traffic-free-system master-prompt #27) - raw observations
    # are kept briefly; the derived historical baseline is kept long-term.
    traffic_raw_retention_days: int = Field(default=7)
    traffic_snapshot_retention_days: int = Field(default=30)

    # Server-side validation limit on one ingestion request (CLAUDE.md #29 - validate
    # everything server-side; never accept an unbounded batch).
    traffic_max_batch_size: int = Field(default=500)

    # QPSO fitness weights (CLAUDE.md #9) - tunable starting values, not a proven-optimal
    # combination. Need not sum to 1; only relative magnitude matters to QPSO.
    distance_weight: float = Field(default=0.4)
    time_weight: float = Field(default=0.4)
    traffic_weight: float = Field(default=0.2)


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance; avoids re-parsing env vars on every call."""
    return Settings()
