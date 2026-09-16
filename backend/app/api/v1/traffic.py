"""Traffic telemetry endpoints (CLAUDE.md #16). No commercial traffic API is involved -
ingestion is QTrace's own anonymized GPS telemetry, map-matched against OSRM.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_traffic_repository, get_traffic_telemetry_service
from app.core.config import Settings, get_settings
from app.repositories.traffic_repository import TrafficRepository
from app.schemas.traffic import (
    TrafficIngestResult,
    TrafficObservationBatchRequest,
    TrafficSegmentSummary,
)
from app.traffic.aggregation import classify_freshness
from app.traffic.service import TrafficTelemetryService

router = APIRouter(prefix="/traffic", tags=["traffic"])


@router.post("/observations", response_model=TrafficIngestResult)
async def ingest_traffic_observations(
    request: TrafficObservationBatchRequest,
    telemetry_service: TrafficTelemetryService = Depends(get_traffic_telemetry_service),
    repository: TrafficRepository = Depends(get_traffic_repository),
    settings: Settings = Depends(get_settings),
) -> TrafficIngestResult:
    """One request = one continuous trace/session (CLAUDE.md #29). Every observation
    is validated server-side (CLAUDE.md #29) - never trust client-reported sanity."""
    if not settings.traffic_telemetry_ingestion_enabled:
        return TrafficIngestResult(
            accepted=0,
            rejected=len(request.observations),
            rejection_reasons=["telemetry ingestion is currently disabled"],
        )
    if len(request.observations) > settings.traffic_max_batch_size:
        raise HTTPException(
            status_code=400,
            detail=f"Batch of {len(request.observations)} exceeds the configured limit "
            f"of {settings.traffic_max_batch_size} (TRAFFIC_MAX_BATCH_SIZE).",
        )

    result = await telemetry_service.ingest_observations(repository, request.observations)
    repository.commit()
    return result


@router.get("/segments", response_model=list[TrafficSegmentSummary])
async def get_traffic_segments(
    west: float = Query(..., ge=-180, le=180),
    south: float = Query(..., ge=-90, le=90),
    east: float = Query(..., ge=-180, le=180),
    north: float = Query(..., ge=-90, le=90),
    repository: TrafficRepository = Depends(get_traffic_repository),
    settings: Settings = Depends(get_settings),
) -> list[TrafficSegmentSummary]:
    """Normalized, provider-agnostic view - never the raw DB row (CLAUDE.md #6.3).
    Freshness/status is recomputed against the CURRENT time here, not trusted from
    whenever the snapshot was last written (CLAUDE.md #17 - a snapshot that was LIVE
    ten minutes ago and never updated since must not still be reported as LIVE)."""
    now = datetime.now(timezone.utc)
    results = repository.get_snapshots_in_bbox(west, south, east, north)

    summaries = []
    for snapshot, segment in results:
        captured_at = snapshot.captured_at
        if captured_at.tzinfo is None:
            captured_at = captured_at.replace(tzinfo=timezone.utc)
        age_seconds = (now - captured_at).total_seconds()
        status = classify_freshness(
            age_seconds,
            settings.traffic_live_ttl_seconds,
            settings.traffic_recent_ttl_seconds,
            settings.traffic_expired_seconds,
        )
        summaries.append(
            TrafficSegmentSummary(
                segment_id=segment.id,
                current_speed_mps=snapshot.current_speed_mps,
                reference_speed_mps=snapshot.reference_speed_mps,
                congestion_score=snapshot.congestion_score,
                status=status,
                confidence=snapshot.confidence,
                observation_count=snapshot.observation_count,
                updated_at=snapshot.captured_at,
            )
        )
    return summaries
