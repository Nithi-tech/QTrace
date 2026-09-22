"""TrafficTelemetryService - QTrace's own crowd-telemetry ingestion (CLAUDE.md #6.2).
Owns validation, map-matching, and snapshot/historical-profile recomputation for the
QTRACE_CROWD tier of the fallback hierarchy (see app/traffic/traffic_service.py for
where TomTom live data is resolved and how the two combine). Never calls a
routing/matching provider more than once per ingested batch.
"""

from datetime import datetime, timedelta, timezone

from app.repositories.traffic_repository import TrafficRepository
from app.routing.map_matching import RoadMatchingProvider
from app.schemas.map_matching import TimedCoordinate
from app.schemas.traffic import TrafficIngestResult, TrafficObservationInput
from app.traffic.aggregation import (
    classify_freshness,
    compute_crowd_confidence,
    congestion_score,
    median_speed_mps,
)
from app.traffic.historical import day_of_week, time_bucket_minutes
from app.traffic.reference_speed import resolve_reference_speed

# Sanity bounds (CLAUDE.md #38) - reject physically implausible input before it ever
# reaches map-matching or storage.
MAX_PLAUSIBLE_SPEED_MPS = 55.0  # ~198 km/h
MAX_USABLE_ACCURACY_M = 100.0


def _as_utc(at: datetime) -> datetime:
    """SQLite (used in unit tests) does not round-trip timezone info the way
    PostgreSQL does, so a value read back from the DB can come back naive even though
    it was always stored as UTC - treat a naive value as UTC rather than guessing."""
    return at if at.tzinfo is not None else at.replace(tzinfo=timezone.utc)


def _validate(observations: list[TrafficObservationInput]) -> tuple[list[TrafficObservationInput], list[str]]:
    valid: list[TrafficObservationInput] = []
    reasons: list[str] = []
    now = datetime.now(timezone.utc)
    for obs in observations:
        timestamp = _as_utc(obs.timestamp)
        if obs.speed_mps > MAX_PLAUSIBLE_SPEED_MPS:
            reasons.append(f"speed_mps {obs.speed_mps} exceeds plausible maximum")
            continue
        if obs.accuracy_m > MAX_USABLE_ACCURACY_M:
            reasons.append(f"accuracy_m {obs.accuracy_m} too poor to be usable")
            continue
        if timestamp > now + timedelta(minutes=5):
            reasons.append("timestamp is in the future")
            continue
        if timestamp < now - timedelta(days=1):
            reasons.append("timestamp is implausibly old for a live telemetry upload")
            continue
        valid.append(obs)
    return valid, reasons


class TrafficTelemetryService:
    def __init__(
        self,
        matching_provider: RoadMatchingProvider,
        min_observations: int,
        live_ttl_seconds: float,
        recent_ttl_seconds: float,
        expired_seconds: float,
        historical_bucket_minutes: int = 15,
    ) -> None:
        self._matching_provider = matching_provider
        self._min_observations = min_observations
        self._live_ttl_seconds = live_ttl_seconds
        self._recent_ttl_seconds = recent_ttl_seconds
        self._expired_seconds = expired_seconds
        self._historical_bucket_minutes = historical_bucket_minutes

    async def ingest_observations(
        self, repository: TrafficRepository, observations: list[TrafficObservationInput]
    ) -> TrafficIngestResult:
        valid, rejection_reasons = _validate(observations)
        num_invalid = len(observations) - len(valid)
        if not valid:
            return TrafficIngestResult(
                accepted=0, rejected=len(observations), rejection_reasons=rejection_reasons
            )

        valid_sorted = sorted(valid, key=lambda o: o.timestamp)
        by_timestamp = {obs.timestamp: obs for obs in valid_sorted}
        points = [
            TimedCoordinate(latitude=o.latitude, longitude=o.longitude, timestamp=o.timestamp)
            for o in valid_sorted
        ]

        match_result = await self._matching_provider.match_trace(points)
        if not match_result.matched:
            return TrafficIngestResult(
                accepted=0,
                rejected=len(observations),
                rejection_reasons=[*rejection_reasons, "trace could not be map-matched to a road"],
            )

        now = datetime.now(timezone.utc)
        latest_per_segment: dict[str, tuple[datetime, float]] = {}
        segment_observations_stored = 0

        for leg in match_result.legs:
            start_obs = by_timestamp.get(leg.start_timestamp)
            end_obs = by_timestamp.get(leg.end_timestamp)
            if start_obs is None or end_obs is None:
                continue
            observed_speed = (start_obs.speed_mps + end_obs.speed_mps) / 2
            accuracy = (start_obs.accuracy_m + end_obs.accuracy_m) / 2

            seen_this_leg: set[str] = set()
            for edge in leg.edges:
                if edge.segment_key in seen_this_leg:
                    continue
                seen_this_leg.add(edge.segment_key)

                segment = repository.get_or_create_segment(
                    node_a=edge.node_a,
                    node_b=edge.node_b,
                    geometry=edge.geometry,
                    profile_speed_mps=edge.profile_speed_mps,
                    now=now,
                )
                repository.add_observation(
                    segment_id=segment.id,
                    observed_speed_mps=observed_speed,
                    accuracy_m=accuracy,
                    recorded_at=end_obs.timestamp,
                    now=now,
                )
                segment_observations_stored += 1

                current_latest = latest_per_segment.get(segment.id)
                if current_latest is None or end_obs.timestamp > current_latest[0]:
                    latest_per_segment[segment.id] = (end_obs.timestamp, observed_speed)

        for segment_id, (recorded_at, speed) in latest_per_segment.items():
            self._update_snapshot(repository, segment_id, now)
            self._update_historical_profile(repository, segment_id, recorded_at=recorded_at, speed_mps=speed)

        return TrafficIngestResult(
            accepted=len(valid),
            rejected=num_invalid,
            rejection_reasons=rejection_reasons,
            segment_observations_stored=segment_observations_stored,
        )

    def _update_snapshot(self, repository: TrafficRepository, segment_id: str, now: datetime) -> None:
        since = now - timedelta(seconds=self._expired_seconds)
        recent = repository.get_recent_observations(segment_id, since=since)
        if not recent:
            # Nothing to summarize yet - no snapshot row is created (absence of data
            # must not be reported as if it were known-low traffic).
            return

        current_speed = median_speed_mps([o.observed_speed_mps for o in recent])
        segment = repository.get_segment(segment_id)
        historical = repository.get_historical_profile(
            segment_id, day_of_week(now), time_bucket_minutes(now, self._historical_bucket_minutes)
        )
        reference = resolve_reference_speed(
            provider_free_flow_speed_mps=segment.profile_speed_mps if segment else None,
            historical_median_mps=historical.median_speed_mps if historical else None,
        )
        age_seconds = (now - max(_as_utc(o.recorded_at) for o in recent)).total_seconds()
        status = classify_freshness(
            age_seconds, self._live_ttl_seconds, self._recent_ttl_seconds, self._expired_seconds
        )
        confidence = compute_crowd_confidence(len(recent), self._min_observations, status)

        repository.upsert_snapshot(
            segment_id=segment_id,
            current_speed_mps=current_speed,
            reference_speed_mps=reference.speed_mps,
            reference_speed_source=reference.source,
            congestion_score=congestion_score(current_speed, reference.speed_mps),
            observation_count=len(recent),
            confidence=confidence,
            status=status,
            captured_at=now,
        )

    def _update_historical_profile(
        self, repository: TrafficRepository, segment_id: str, recorded_at: datetime, speed_mps: float
    ) -> None:
        """Bucketed by the observation's own GPS timestamp - a batch uploaded late, or
        backfilled, still lands in the historical bucket it actually happened in."""
        repository.upsert_historical_profile(
            segment_id=segment_id,
            day_of_week=day_of_week(recorded_at),
            time_bucket_minutes=time_bucket_minutes(recorded_at, self._historical_bucket_minutes),
            new_speed_sample=speed_mps,
            now=datetime.now(timezone.utc),
        )
