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

    # Real-time traffic intelligence (docs/TRAFFIC_ARCHITECTURE.md). Fallback order:
    # TomTom live -> QTrace crowd telemetry -> historical baseline -> unavailable.
    traffic_enabled: bool = Field(default=True)
    traffic_telemetry_ingestion_enabled: bool = Field(default=True)

    traffic_timeout_seconds: float = Field(default=5.0)
    traffic_max_retries: int = Field(default=2)
    # TomTom flow/incident responses are cached in-process (no Redis client exists yet
    # in this codebase - CLAUDE.md #46 don't add infra a feature doesn't need; a
    # Redis-backed cache is a documented follow-up, not built in this pass).
    traffic_cache_ttl_seconds: float = Field(default=60.0)

    # Freshness thresholds (never labeled LIVE/RECENT past these ages).
    traffic_live_ttl_seconds: float = Field(default=120.0)
    traffic_recent_ttl_seconds: float = Field(default=300.0)
    traffic_expired_seconds: float = Field(default=900.0)

    # A crowd-telemetry segment's snapshot isn't trusted until this many independent
    # observations back it.
    traffic_min_observations: int = Field(default=3)

    # Corridor width used to match a stop-pair to nearby crowd segments / incidents.
    traffic_corridor_radius_meters: float = Field(default=150.0)

    traffic_raw_retention_days: int = Field(default=7)
    traffic_snapshot_retention_days: int = Field(default=30)
    traffic_max_batch_size: int = Field(default=500)

    # QPSO fitness weights (CLAUDE.md #9) - tunable starting values, not a proven-optimal
    # combination. Need not sum to 1; only relative magnitude matters to QPSO.
    distance_weight: float = Field(default=0.4)
    time_weight: float = Field(default=0.4)
    traffic_weight: float = Field(default=0.2)

    # Map traffic layer (GET /api/v1/traffic/area, docs/TRAFFIC_ARCHITECTURE.md) - a
    # Google-Maps-style colored-roads overlay, separate from the QPSO/route-status
    # fallback hierarchy above. TomTom's flow API is point-based (no bbox endpoint), so
    # the area is covered by a capped grid of point samples, never one call per pixel
    # and never an unbounded viewport (CLAUDE.md traffic master-prompt #18/#19).
    traffic_area_max_points: int = Field(default=36)
    traffic_area_max_span_degrees: float = Field(default=0.25)

    # 5-level map visualization thresholds on speed_ratio (current/free-flow) - QTrace's
    # own classification, not any provider's or Google's (CLAUDE.md traffic master-prompt
    # #8). Descending: >= green -> FREE_FLOW, >= yellow -> MODERATE, >= orange -> HEAVY,
    # >= red -> VERY_HEAVY, below red -> SEVERE.
    traffic_map_green_threshold: float = Field(default=0.80)
    traffic_map_yellow_threshold: float = Field(default=0.60)
    traffic_map_orange_threshold: float = Field(default=0.40)
    traffic_map_red_threshold: float = Field(default=0.20)


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance; avoids re-parsing env vars on every call."""
    return Settings()
