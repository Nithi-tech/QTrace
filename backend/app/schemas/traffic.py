"""Traffic domain data contracts (CLAUDE.md #6.3).

TrafficStatus is what every optimization response reports (CLAUDE.md traffic-free-
system master-prompt #24) - it is the single source of truth for whether real,
sufficiently-confident QTrace telemetry was used, versus no data (`available=False`).
Never fabricated: `live` and `available` come directly from what
app/traffic/matrix_service.py actually found, not an assumption.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class TrafficObservationInput(BaseModel):
    """One raw GPS sample from the Android client (CLAUDE.md traffic-free-system
    master-prompt #7 - only what's needed, nothing identifying)."""

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    speed_mps: float = Field(ge=0)
    heading: float | None = Field(default=None, ge=0, le=360)
    accuracy_m: float = Field(gt=0)
    timestamp: datetime


class TrafficObservationBatchRequest(BaseModel):
    observations: list[TrafficObservationInput]


class TrafficIngestResult(BaseModel):
    """accepted/rejected count the caller's own uploaded observations (so accepted +
    rejected == len(request.observations), always) - not the internal number of
    per-road-segment rows written, which is reported separately since one short trace
    can legitimately span many segments and so exceed the input observation count."""

    accepted: int
    rejected: int
    rejection_reasons: list[str] = Field(default_factory=list)
    segment_observations_stored: int = Field(
        default=0, description="Internal row count - can exceed `accepted` (one trace spans many segments)."
    )


class TrafficStatus(BaseModel):
    enabled: bool
    available: bool = Field(description="Whether any usable QTrace telemetry existed for this request.")
    source: str = Field(description='"qtrace_telemetry" when available, "unavailable" otherwise.')
    live: bool
    confidence: float | None = None
    updated_at: datetime | None = None


class TrafficSegmentSummary(BaseModel):
    """Normalized, provider-agnostic view of a segment's current state - never the
    raw DB row (CLAUDE.md #6.3)."""

    segment_id: str
    current_speed_mps: float | None
    reference_speed_mps: float | None
    congestion_score: float | None
    status: str
    confidence: float | None
    observation_count: int
    updated_at: datetime | None
