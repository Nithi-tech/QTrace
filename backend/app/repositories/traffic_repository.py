"""Traffic telemetry persistence (CLAUDE.md #6.2 - Service -> Repository -> Database).

All timestamps are stored and compared as UTC (CLAUDE.md #40).
"""

from datetime import datetime, timedelta

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.traffic_historical_profile import TrafficHistoricalProfile
from app.models.traffic_observation import TrafficObservation
from app.models.traffic_segment import TrafficSegment
from app.models.traffic_snapshot import TrafficSnapshot


class TrafficRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def commit(self) -> None:
        self._db.commit()

    def get_or_create_segment(
        self, node_a: int, node_b: int, geometry: dict | None, profile_speed_mps: float | None, now: datetime
    ) -> TrafficSegment:
        low, high = min(node_a, node_b), max(node_a, node_b)
        existing = (
            self._db.query(TrafficSegment)
            .filter(TrafficSegment.node_a == low, TrafficSegment.node_b == high)
            .one_or_none()
        )
        if existing is not None:
            return existing

        segment = TrafficSegment(
            node_a=low, node_b=high, geometry=geometry, profile_speed_mps=profile_speed_mps, created_at=now
        )
        self._db.add(segment)
        self._db.flush()  # assigns segment.id without committing the whole ingestion batch yet
        return segment

    def add_observation(
        self,
        segment_id: str,
        observed_speed_mps: float,
        accuracy_m: float,
        recorded_at: datetime,
        now: datetime,
    ) -> TrafficObservation:
        observation = TrafficObservation(
            segment_id=segment_id,
            observed_speed_mps=observed_speed_mps,
            accuracy_m=accuracy_m,
            recorded_at=recorded_at,
            created_at=now,
        )
        self._db.add(observation)
        return observation

    def get_recent_observations(
        self, segment_id: str, since: datetime, limit: int = 200
    ) -> list[TrafficObservation]:
        return (
            self._db.query(TrafficObservation)
            .filter(TrafficObservation.segment_id == segment_id, TrafficObservation.recorded_at >= since)
            .order_by(TrafficObservation.recorded_at.desc())
            .limit(limit)
            .all()
        )

    def get_segment(self, segment_id: str) -> TrafficSegment | None:
        return self._db.get(TrafficSegment, segment_id)

    def get_snapshot(self, segment_id: str) -> TrafficSnapshot | None:
        return self._db.query(TrafficSnapshot).filter(TrafficSnapshot.segment_id == segment_id).one_or_none()

    def upsert_snapshot(
        self,
        segment_id: str,
        current_speed_mps: float,
        reference_speed_mps: float,
        congestion_score: float,
        observation_count: int,
        confidence: float,
        status: str,
        captured_at: datetime,
    ) -> TrafficSnapshot:
        snapshot = self.get_snapshot(segment_id)
        if snapshot is None:
            snapshot = TrafficSnapshot(
                provider="qtrace_telemetry",
                road_or_route_info={"segment_id": segment_id},
                segment_id=segment_id,
                captured_at=captured_at,
            )
            self._db.add(snapshot)

        snapshot.captured_at = captured_at
        snapshot.current_speed_mps = current_speed_mps
        snapshot.reference_speed_mps = reference_speed_mps
        snapshot.congestion_score = congestion_score
        snapshot.observation_count = observation_count
        snapshot.confidence = confidence
        snapshot.status = status
        return snapshot

    def get_snapshots_in_bbox(
        self, west: float, south: float, east: float, north: float
    ) -> list[tuple[TrafficSnapshot, TrafficSegment]]:
        """Bounding-box filter over each segment's geometry.

        Geometry is stored as JSON (not a PostGIS geometry column in this pass - see
        docs/TRAFFIC_ARCHITECTURE.md), so filtering happens in Python rather than via a
        spatial SQL predicate. Fine at the data volumes this feature currently operates
        at; a real spatial index is a documented future upgrade.
        """
        results = (
            self._db.query(TrafficSnapshot, TrafficSegment)
            .join(TrafficSegment, TrafficSnapshot.segment_id == TrafficSegment.id)
            .all()
        )
        matched = []
        for snapshot, segment in results:
            if not segment.geometry:
                continue
            coords = segment.geometry.get("coordinates", [])
            if any(west <= lon <= east and south <= lat <= north for lon, lat in coords):
                matched.append((snapshot, segment))
        return matched

    def get_historical_profile(
        self, segment_id: str, day_of_week: int, time_bucket_minutes: int
    ) -> TrafficHistoricalProfile | None:
        return (
            self._db.query(TrafficHistoricalProfile)
            .filter(
                TrafficHistoricalProfile.segment_id == segment_id,
                TrafficHistoricalProfile.day_of_week == day_of_week,
                TrafficHistoricalProfile.time_bucket_minutes == time_bucket_minutes,
            )
            .one_or_none()
        )

    def upsert_historical_profile(
        self,
        segment_id: str,
        day_of_week: int,
        time_bucket_minutes: int,
        new_speed_sample: float,
        now: datetime,
    ) -> TrafficHistoricalProfile:
        """Running-mean update (CLAUDE.md traffic-free-system master-prompt #14) -
        see app/models/traffic_historical_profile.py docstring for why this is a mean,
        not a true rolling median."""
        profile = self.get_historical_profile(segment_id, day_of_week, time_bucket_minutes)
        if profile is None:
            profile = TrafficHistoricalProfile(
                segment_id=segment_id,
                day_of_week=day_of_week,
                time_bucket_minutes=time_bucket_minutes,
                median_speed_mps=new_speed_sample,
                sample_count=1,
                updated_at=now,
            )
            self._db.add(profile)
            return profile

        profile.median_speed_mps = (profile.median_speed_mps * profile.sample_count + new_speed_sample) / (
            profile.sample_count + 1
        )
        profile.sample_count += 1
        profile.updated_at = now
        return profile

    def purge_expired(self, raw_cutoff: datetime, snapshot_cutoff: datetime) -> tuple[int, int]:
        """Deletes raw observations older than raw_cutoff and orphaned/expired
        snapshots older than snapshot_cutoff (CLAUDE.md traffic-free-system
        master-prompt #27 - short raw retention, longer aggregate retention)."""
        observations_deleted = (
            self._db.query(TrafficObservation).filter(TrafficObservation.created_at < raw_cutoff).delete()
        )
        snapshots_deleted = (
            self._db.query(TrafficSnapshot)
            .filter(
                and_(TrafficSnapshot.segment_id.isnot(None), TrafficSnapshot.captured_at < snapshot_cutoff)
            )
            .delete()
        )
        return observations_deleted, snapshots_deleted


def retention_cutoffs(
    now: datetime, raw_retention_days: int, snapshot_retention_days: int
) -> tuple[datetime, datetime]:
    return now - timedelta(days=raw_retention_days), now - timedelta(days=snapshot_retention_days)
