"""Traffic domain data contracts (CLAUDE.md #6.3) - normalized, provider-independent.

Raw TomTom JSON never leaves app/traffic/tomtom_provider.py; raw crowd-telemetry rows
never leave the repository layer. Everything downstream (matching, scoring, QPSO
blending, API responses) works only with these models.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class TrafficFlowSegment(BaseModel):
    """One road segment's current flow, from whichever provider supplied it."""

    geometry: dict | None = None  # GeoJSON LineString, when the provider returns one
    current_speed_mps: float
    free_flow_speed_mps: float
    confidence: float | None = None  # provider-native confidence, when available (e.g. TomTom's own)


class TrafficIncident(BaseModel):
    geometry: dict | None = None
    incident_type: str
    delay_seconds: float | None = None
    severity: float | None = None  # 0-10 scale, see app/traffic/tomtom_provider.py
    road_closed: bool = False


class TrafficObservationInput(BaseModel):
    """One raw GPS sample from an opted-in Android client (CLAUDE.md traffic master-
    prompt #19 - only what's needed, nothing identifying)."""

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    speed_mps: float = Field(ge=0)
    heading: float | None = Field(default=None, ge=0, le=360)
    accuracy_m: float = Field(gt=0)
    timestamp: datetime


class TrafficObservationBatchRequest(BaseModel):
    observations: list[TrafficObservationInput]


class TrafficIngestResult(BaseModel):
    """accepted/rejected count the caller's own uploaded observations (accepted +
    rejected == len(request.observations), always) - not the internal per-segment row
    count, which is reported separately since one trace can span many segments."""

    accepted: int
    rejected: int
    rejection_reasons: list[str] = Field(default_factory=list)
    segment_observations_stored: int = 0


class TrafficStatus(BaseModel):
    """What every optimization response reports (CLAUDE.md traffic master-prompt #30) -
    the single source of truth for whether real traffic data was used, and from where."""

    enabled: bool
    available: bool
    status: str = Field(description="LIVE / RECENT / STALE / HISTORICAL / UNAVAILABLE")
    source: str | None = Field(default=None, description='"TOMTOM", "QTRACE_CROWD", "HISTORICAL", or null.')
    confidence: float | None = None
    updated_at: datetime | None = None
    level: str | None = Field(
        default=None,
        description=(
            "LOW / MODERATE / HEAVY - QTrace's own congestion classification for the "
            "route actually planned (app/traffic/aggregation.py::classify_traffic_level), "
            "not any provider's label. Null when traffic is unavailable."
        ),
    )


class TrafficSegmentSummary(BaseModel):
    """Normalized, provider-agnostic view of a segment's current state - never the
    raw DB row."""

    segment_id: str
    current_speed_mps: float | None
    reference_speed_mps: float | None
    reference_speed_source: str | None
    congestion_score: float | None
    status: str
    source: str | None
    confidence: float | None
    observation_count: int
    updated_at: datetime | None


class TrafficSegmentFeature(BaseModel):
    """One real, TomTom-returned road segment for the map traffic layer
    (docs/TRAFFIC_ARCHITECTURE.md - Google-Maps-style visualization). geometry is the
    exact GeoJSON LineString TomTom reported near the sampled point - never a fabricated
    or straight-line shape. Speeds are km/h here (not m/s like the rest of this module)
    because this endpoint is consumed directly by the map UI, where km/h is the natural
    display unit - converted once, at this API boundary (CLAUDE.md #39)."""

    id: str
    geometry: dict
    current_speed_kph: float
    free_flow_speed_kph: float
    speed_ratio: float = Field(description="current/free_flow, clamped to [0, 1]")
    congestion_level: str = Field(description="FREE_FLOW / MODERATE / HEAVY / VERY_HEAVY / SEVERE")
    confidence: float | None = None


class TrafficAreaResponse(BaseModel):
    """GET /api/v1/traffic/area - a real, sampled snapshot of TomTom flow across a
    bounded viewport (never an entire city/world - CLAUDE.md traffic master-prompt
    #18/#19). enabled=false or an empty segments list must never be presented as
    "no traffic" - the map UI must show it as unavailable, not free-flowing."""

    enabled: bool
    status: str = Field(description="LIVE / UNAVAILABLE")
    source: str | None = None
    updated_at: datetime | None = None
    segments: list[TrafficSegmentFeature] = Field(default_factory=list)
