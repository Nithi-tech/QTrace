"""Traffic endpoints (CLAUDE.md #16, docs/TRAFFIC_ARCHITECTURE.md).

/point resolves the full TomTom -> QTrace crowd -> historical fallback hierarchy for one
coordinate (used by QPSO's traffic matrix and available here for inspection). /area is
the map-visualization endpoint: real TomTom flow sampled across a bounded grid over a
viewport (app/traffic/area_sampler.py) - there is no true "every segment in this bbox"
endpoint in TomTom's plain-JSON API, so this is the legitimate way to cover an area
without fabricating geometry (CLAUDE.md traffic master-prompt #4/#8).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import (
    get_traffic_area_sampler,
    get_traffic_repository,
    get_traffic_service,
    get_traffic_telemetry_service,
)
from app.core.config import Settings, get_settings
from app.repositories.traffic_repository import TrafficRepository
from app.schemas.routing import Coordinate
from app.schemas.traffic import (
    TrafficAreaResponse,
    TrafficIngestResult,
    TrafficObservationBatchRequest,
    TrafficSegmentFeature,
    TrafficSegmentSummary,
    TrafficStatus,
)
from app.traffic.aggregation import classify_map_traffic_level, classify_traffic_level, speed_ratio
from app.traffic.area_sampler import SampledSegment, TrafficAreaSampler
from app.traffic.telemetry_service import TrafficTelemetryService
from app.traffic.traffic_service import TrafficService

router = APIRouter(prefix="/traffic", tags=["traffic"])

_MPS_TO_KMPH = 3.6
_UNAVAILABLE_AREA = TrafficAreaResponse(enabled=True, status="UNAVAILABLE", source=None, segments=[])


@router.post("/observations", response_model=TrafficIngestResult)
async def ingest_observations(
    request: TrafficObservationBatchRequest,
    telemetry_service: TrafficTelemetryService = Depends(get_traffic_telemetry_service),
    traffic_repository: TrafficRepository = Depends(get_traffic_repository),
    settings: Settings = Depends(get_settings),
) -> TrafficIngestResult:
    """Crowd-telemetry ingestion from an opted-in Android client. Feeds the
    QTRACE_CROWD tier of the fallback hierarchy - never TomTom's tier, and never
    consulted from inside QPSO's fitness loop."""
    if not settings.traffic_telemetry_ingestion_enabled:
        return TrafficIngestResult(
            accepted=0,
            rejected=len(request.observations),
            rejection_reasons=["telemetry ingestion is disabled (TRAFFIC_TELEMETRY_INGESTION_ENABLED=false)"],
        )
    if len(request.observations) > settings.traffic_max_batch_size:
        raise HTTPException(
            status_code=400,
            detail=f"Batch of {len(request.observations)} exceeds TRAFFIC_MAX_BATCH_SIZE "
            f"({settings.traffic_max_batch_size}).",
        )
    result = await telemetry_service.ingest_observations(traffic_repository, request.observations)
    traffic_repository.commit()
    return result


@router.get("/point", response_model=TrafficStatus)
async def get_traffic_at_point(
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    traffic_service: TrafficService = Depends(get_traffic_service),
    traffic_repository: TrafficRepository = Depends(get_traffic_repository),
    settings: Settings = Depends(get_settings),
) -> TrafficStatus:
    """The same TomTom -> QTrace crowd -> historical -> unavailable resolution used
    internally per-stop when building an optimization request's traffic matrix
    (app/traffic/matrix_service.py), exposed directly for inspection/debugging."""
    if not settings.traffic_enabled:
        return TrafficStatus(enabled=False, available=False, status="UNAVAILABLE", source=None)

    resolved = await traffic_service.resolve(
        traffic_repository, Coordinate(latitude=latitude, longitude=longitude)
    )
    return TrafficStatus(
        enabled=True,
        available=resolved.available,
        status=resolved.status,
        source=resolved.source,
        confidence=resolved.confidence if resolved.available else None,
        updated_at=resolved.updated_at,
        level=classify_traffic_level(resolved.congestion_score) if resolved.available else None,
    )


@router.get("/segments/{segment_id}", response_model=TrafficSegmentSummary)
async def get_segment_summary(
    segment_id: str,
    traffic_repository: TrafficRepository = Depends(get_traffic_repository),
) -> TrafficSegmentSummary:
    """QTrace's own view of one road segment - the crowd-telemetry snapshot only
    (TomTom's live data is never persisted, so it has no segment_id to look up)."""
    segment = traffic_repository.get_segment(segment_id)
    if segment is None:
        raise HTTPException(status_code=404, detail=f"Traffic segment {segment_id!r} not found")

    snapshot = traffic_repository.get_snapshot(segment_id)
    return TrafficSegmentSummary(
        segment_id=segment_id,
        current_speed_mps=snapshot.current_speed_mps if snapshot else None,
        reference_speed_mps=snapshot.reference_speed_mps if snapshot else None,
        reference_speed_source=snapshot.reference_speed_source if snapshot else None,
        congestion_score=snapshot.congestion_score if snapshot else None,
        status=snapshot.status if snapshot else "UNAVAILABLE",
        source="QTRACE_CROWD" if snapshot else None,
        confidence=snapshot.confidence if snapshot else None,
        observation_count=snapshot.observation_count if snapshot else 0,
        updated_at=snapshot.captured_at if snapshot else None,
    )


@router.get("/area", response_model=TrafficAreaResponse)
async def get_traffic_area(
    min_lat: float = Query(ge=-90, le=90),
    min_lon: float = Query(ge=-180, le=180),
    max_lat: float = Query(ge=-90, le=90),
    max_lon: float = Query(ge=-180, le=180),
    sampler: TrafficAreaSampler = Depends(get_traffic_area_sampler),
    settings: Settings = Depends(get_settings),
) -> TrafficAreaResponse:
    """Google-Maps-style colored-roads layer for the map (docs/TRAFFIC_ARCHITECTURE.md).
    Never fabricates a segment: every returned geometry is exactly what TomTom reported
    near a sampled point (CLAUDE.md traffic master-prompt #4)."""
    if not settings.traffic_enabled:
        return TrafficAreaResponse(enabled=False, status="UNAVAILABLE", source=None, segments=[])
    if max_lat <= min_lat or max_lon <= min_lon:
        raise HTTPException(status_code=400, detail="max_lat/max_lon must exceed min_lat/min_lon")

    span_degrees = max(max_lat - min_lat, max_lon - min_lon)
    if span_degrees > settings.traffic_area_max_span_degrees:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Requested area spans {span_degrees:.3f} degrees; the limit is "
                f"{settings.traffic_area_max_span_degrees} (TRAFFIC_AREA_MAX_SPAN_DEGREES). "
                "Zoom in to view traffic."
            ),
        )

    sampled = await sampler.sample(min_lon, min_lat, max_lon, max_lat)
    if not sampled:
        return _UNAVAILABLE_AREA

    return TrafficAreaResponse(
        enabled=True,
        status="LIVE",
        source="TOMTOM",
        updated_at=datetime.now(timezone.utc),
        segments=[_to_feature(segment, settings) for segment in sampled],
    )


def _to_feature(segment: SampledSegment, settings: Settings) -> TrafficSegmentFeature:
    ratio = speed_ratio(segment.current_speed_mps, segment.free_flow_speed_mps)
    level = classify_map_traffic_level(
        ratio,
        green_threshold=settings.traffic_map_green_threshold,
        yellow_threshold=settings.traffic_map_yellow_threshold,
        orange_threshold=settings.traffic_map_orange_threshold,
        red_threshold=settings.traffic_map_red_threshold,
    )
    coordinates = segment.geometry.get("coordinates") or []
    endpoints = (tuple(coordinates[0]), tuple(coordinates[-1])) if coordinates else ()
    return TrafficSegmentFeature(
        id=f"seg-{abs(hash(endpoints)) % 10**8}",
        geometry=segment.geometry,
        current_speed_kph=segment.current_speed_mps * _MPS_TO_KMPH,
        free_flow_speed_kph=segment.free_flow_speed_mps * _MPS_TO_KMPH,
        speed_ratio=ratio,
        congestion_level=level,
        confidence=segment.confidence,
    )
