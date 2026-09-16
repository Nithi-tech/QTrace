"""TrafficMatrixService - the read/optimization-time half of the QTrace crowd-traffic
system (CLAUDE.md #6.2). Queries already-stored snapshots once per optimization
request; never touches the ingestion path, never calls a routing/matching provider,
and never runs inside the QPSO loop (CLAUDE.md traffic-free-system master-prompt #22).
"""

from dataclasses import dataclass
from datetime import datetime

from app.repositories.traffic_repository import TrafficRepository
from app.schemas.routing import Coordinate
from app.schemas.traffic import TrafficStatus
from app.traffic.matcher import build_bounding_box, match_pair_to_snapshots


@dataclass
class TrafficMatrixResult:
    matrix: list[list[float]]
    status: TrafficStatus


def _baseline(num_stops: int, enabled: bool) -> TrafficMatrixResult:
    return TrafficMatrixResult(
        matrix=[[0.0] * num_stops for _ in range(num_stops)],
        status=TrafficStatus(enabled=enabled, available=False, source="unavailable", live=False),
    )


class TrafficMatrixService:
    def __init__(self, corridor_radius_meters: float) -> None:
        self._corridor_radius_meters = corridor_radius_meters

    def get_traffic_matrix(
        self, repository: TrafficRepository, stops: list[Coordinate], enabled: bool
    ) -> TrafficMatrixResult:
        if not enabled:
            return _baseline(len(stops), enabled=False)

        west, south, east, north = build_bounding_box(stops, self._corridor_radius_meters)
        candidates = repository.get_snapshots_in_bbox(west, south, east, north)
        if not candidates:
            return _baseline(len(stops), enabled=True)

        size = len(stops)
        matrix = [[0.0] * size for _ in range(size)]
        cell_confidences: list[float] = []
        any_available = False
        any_live = False
        latest_captured_at: datetime | None = None

        for i in range(size):
            for j in range(size):
                if i == j:
                    continue
                matched = match_pair_to_snapshots(
                    stops[i], stops[j], candidates, self._corridor_radius_meters
                )
                usable = [
                    (snap, seg)
                    for snap, seg in matched
                    if snap.congestion_score is not None and snap.confidence
                ]
                if not usable:
                    continue

                total_confidence = sum(snap.confidence for snap, _ in usable)
                if total_confidence <= 0:
                    continue
                weighted_congestion = sum(snap.congestion_score * snap.confidence for snap, _ in usable)
                avg_congestion = weighted_congestion / total_confidence
                avg_confidence = total_confidence / len(usable)

                # Confidence-weighted effective score (CLAUDE.md traffic-free-system
                # master-prompt #50: effective_traffic_weight = traffic_weight *
                # confidence) - baked in here so app/optimization/fitness.py stays a
                # generic blender with no traffic-specific confidence logic of its own.
                matrix[i][j] = avg_congestion * avg_confidence

                any_available = True
                cell_confidences.append(avg_confidence)
                if any(snap.status == "LIVE" for snap, _ in usable):
                    any_live = True
                for snap, _ in usable:
                    if latest_captured_at is None or snap.captured_at > latest_captured_at:
                        latest_captured_at = snap.captured_at

        if not any_available:
            return _baseline(size, enabled=True)

        status = TrafficStatus(
            enabled=True,
            available=True,
            source="qtrace_telemetry",
            live=any_live,
            confidence=sum(cell_confidences) / len(cell_confidences),
            updated_at=latest_captured_at,
        )
        return TrafficMatrixResult(matrix=matrix, status=status)
