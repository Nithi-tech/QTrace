"""TrafficService - resolves the fallback hierarchy for one location (CLAUDE.md
traffic master-prompt #23):

    TomTom LIVE -> fresh + valid? -> use it
                -> else -> QTrace Crowd -> fresh + valid? -> use it
                                        -> else -> Historical -> sufficient? -> use it
                                                                -> else -> UNAVAILABLE

Called once per UNIQUE stop coordinate when building an optimization request's traffic
matrix (app/traffic/matrix_service.py) - never once per QPSO particle/iteration, and
never once per stop-pair (CLAUDE.md traffic master-prompt #26).
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from app.repositories.traffic_repository import TrafficRepository
from app.routing.map_matching import RoadMatchingProvider
from app.schemas.routing import Coordinate
from app.traffic.aggregation import (
    HISTORICAL,
    LIVE,
    UNAVAILABLE,
    classify_freshness,
    congestion_score,
)
from app.traffic.cache import TTLCache
from app.traffic.exceptions import TrafficProviderError
from app.traffic.historical import day_of_week, time_bucket_minutes
from app.traffic.tomtom_provider import TomTomTrafficProvider

# Historical estimates are inherently less trustworthy than any live measurement -
# discounted regardless of how many samples back them (CLAUDE.md traffic master-prompt
# #16). Not claimed to be statistically calibrated - a documented QTrace engineering
# choice, not an industry standard.
_HISTORICAL_CONFIDENCE_FACTOR = 0.5


@dataclass
class ResolvedTraffic:
    available: bool
    status: str  # LIVE / RECENT / STALE / HISTORICAL / UNAVAILABLE
    source: str | None  # TOMTOM / QTRACE_CROWD / HISTORICAL / None
    congestion_score: float  # 0 when unavailable - callers must check `available`, not assume 0=free-flowing
    confidence: float
    updated_at: datetime | None


_UNAVAILABLE = ResolvedTraffic(
    available=False, status=UNAVAILABLE, source=None, congestion_score=0.0, confidence=0.0, updated_at=None
)


class TrafficService:
    def __init__(
        self,
        tomtom_provider: TomTomTrafficProvider | None,
        matching_provider: RoadMatchingProvider,
        cache: TTLCache,
        live_ttl_seconds: float,
        recent_ttl_seconds: float,
        expired_seconds: float,
        min_observations: int,
        historical_bucket_minutes: int = 15,
    ) -> None:
        self._tomtom_provider = tomtom_provider
        self._matching_provider = matching_provider
        self._cache = cache
        self._live_ttl_seconds = live_ttl_seconds
        self._recent_ttl_seconds = recent_ttl_seconds
        self._expired_seconds = expired_seconds
        self._min_observations = min_observations
        self._historical_bucket_minutes = historical_bucket_minutes

    async def resolve(self, repository: TrafficRepository, coordinate: Coordinate) -> ResolvedTraffic:
        tomtom_result = await self._try_tomtom(coordinate)
        if tomtom_result is not None:
            return tomtom_result

        segment_id = await self._resolve_db_segment_id(repository, coordinate)

        crowd_result = self._try_crowd(repository, segment_id)
        if crowd_result is not None:
            return crowd_result

        historical_result = self._try_historical(repository, segment_id)
        if historical_result is not None:
            return historical_result

        return _UNAVAILABLE

    async def _resolve_db_segment_id(
        self, repository: TrafficRepository, coordinate: Coordinate
    ) -> str | None:
        """Snaps a coordinate to the nearest OSM edge, then looks up whether QTrace
        already has a crowd-telemetry segment row for that exact edge (None if no
        QTrace user has ever driven it - not the same as "OSRM couldn't snap the
        point", which also returns None here, deliberately: either way, there is
        nothing for the crowd/historical tiers to use)."""
        snap = await self._matching_provider.snap_point(coordinate)
        if not snap.matched or snap.edge is None:
            return None
        segment = repository.find_segment_by_nodes(snap.edge.node_a, snap.edge.node_b)
        return segment.id if segment else None

    async def _try_tomtom(self, coordinate: Coordinate) -> ResolvedTraffic | None:
        if self._tomtom_provider is None:
            return None

        cache_key = (round(coordinate.latitude, 4), round(coordinate.longitude, 4))
        cached = self._cache.get(cache_key)
        if cached is not None:
            flow = cached
        else:
            try:
                flow = await self._tomtom_provider.get_flow_at_point(coordinate)
            except TrafficProviderError:
                flow = None
            self._cache.set(cache_key, flow)

        if flow is None:
            return None

        return ResolvedTraffic(
            available=True,
            status=LIVE,
            source="TOMTOM",
            congestion_score=congestion_score(flow.current_speed_mps, flow.free_flow_speed_mps),
            confidence=flow.confidence if flow.confidence is not None else 0.8,
            updated_at=datetime.now(timezone.utc),
        )

    def _try_crowd(self, repository: TrafficRepository, segment_id: str | None) -> ResolvedTraffic | None:
        if segment_id is None:
            return None
        snapshot = repository.get_snapshot(segment_id)
        if snapshot is None or snapshot.congestion_score is None or snapshot.confidence is None:
            return None

        now = datetime.now(timezone.utc)
        captured_at = snapshot.captured_at
        if captured_at.tzinfo is None:
            captured_at = captured_at.replace(tzinfo=timezone.utc)
        age_seconds = (now - captured_at).total_seconds()
        status = classify_freshness(
            age_seconds, self._live_ttl_seconds, self._recent_ttl_seconds, self._expired_seconds
        )
        if status in (LIVE, "RECENT"):
            return ResolvedTraffic(
                available=True,
                status=status,
                source="QTRACE_CROWD",
                congestion_score=snapshot.congestion_score,
                confidence=snapshot.confidence,
                updated_at=captured_at,
            )
        return None

    def _try_historical(
        self, repository: TrafficRepository, segment_id: str | None
    ) -> ResolvedTraffic | None:
        if segment_id is None:
            return None
        now = datetime.now(timezone.utc)
        profile = repository.get_historical_profile(
            segment_id, day_of_week(now), time_bucket_minutes(now, self._historical_bucket_minutes)
        )
        if profile is None or profile.sample_count < self._min_observations:
            return None

        segment = repository.get_segment(segment_id)
        reference_speed = segment.profile_speed_mps if segment and segment.profile_speed_mps else None
        if reference_speed is None:
            return None

        count_factor = min(1.0, profile.sample_count / (self._min_observations * 3))
        return ResolvedTraffic(
            available=True,
            status=HISTORICAL,
            source="HISTORICAL",
            congestion_score=congestion_score(profile.median_speed_mps, reference_speed),
            confidence=count_factor * _HISTORICAL_CONFIDENCE_FACTOR,
            updated_at=profile.updated_at,
        )
