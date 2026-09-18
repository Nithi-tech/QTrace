"""TrafficMatrixService - the read/optimization-time entry point for the whole traffic
system (CLAUDE.md #6.2). Resolves every unique stop's traffic once (concurrently, via
TrafficService's TomTom->crowd->historical fallback), fetches incidents once (a single
bbox covering the whole request), and combines them into one N x N matrix. Never
touches QPSO's fitness loop, never calls a provider once per pair or per iteration
(CLAUDE.md traffic master-prompt #26).
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime

from app.repositories.traffic_repository import TrafficRepository
from app.schemas.routing import Coordinate
from app.schemas.traffic import TrafficStatus
from app.traffic.exceptions import TrafficProviderError
from app.traffic.matcher import build_bounding_box, incidents_on_corridor
from app.traffic.tomtom_provider import TomTomTrafficProvider
from app.traffic.traffic_service import ResolvedTraffic, TrafficService

_STATUS_PRIORITY = ("LIVE", "RECENT", "STALE", "HISTORICAL")
_SOURCE_PRIORITY = ("TOMTOM", "QTRACE_CROWD", "HISTORICAL")


@dataclass
class TrafficMatrixResult:
    matrix: list[list[float]]
    status: TrafficStatus


def _baseline(num_stops: int, enabled: bool) -> TrafficMatrixResult:
    return TrafficMatrixResult(
        matrix=[[0.0] * num_stops for _ in range(num_stops)],
        status=TrafficStatus(enabled=enabled, available=False, status="UNAVAILABLE", source=None),
    )


def _best(values: set[str], priority: tuple[str, ...]) -> str | None:
    for candidate in priority:
        if candidate in values:
            return candidate
    return None


class TrafficMatrixService:
    def __init__(
        self,
        traffic_service: TrafficService,
        tomtom_provider: TomTomTrafficProvider | None,
        corridor_radius_meters: float,
    ) -> None:
        self._traffic_service = traffic_service
        self._tomtom_provider = tomtom_provider
        self._corridor_radius_meters = corridor_radius_meters

    async def get_traffic_matrix(
        self, repository: TrafficRepository, stops: list[Coordinate], enabled: bool
    ) -> TrafficMatrixResult:
        if not enabled:
            return _baseline(len(stops), enabled=False)

        resolved: list[ResolvedTraffic] = await asyncio.gather(
            *(self._traffic_service.resolve(repository, stop) for stop in stops)
        )
        incidents = await self._fetch_incidents(stops)

        size = len(stops)
        matrix = [[0.0] * size for _ in range(size)]
        confidences: list[float] = []
        statuses_seen: set[str] = set()
        sources_seen: set[str] = set()
        latest_updated_at: datetime | None = None

        for i in range(size):
            for j in range(size):
                if i == j:
                    continue
                usable = [r for r in (resolved[i], resolved[j]) if r.available]
                if not usable:
                    continue

                total_confidence = sum(r.confidence for r in usable)
                avg_confidence = total_confidence / len(usable)
                avg_congestion = (
                    sum(r.congestion_score * r.confidence for r in usable) / total_confidence
                    if total_confidence > 0
                    else sum(r.congestion_score for r in usable) / len(usable)
                )

                incident_penalty = 0.0
                for incident in incidents_on_corridor(
                    stops[i], stops[j], incidents, self._corridor_radius_meters
                ):
                    penalty = 1.0 if incident.road_closed else (incident.severity or 0.0) / 10.0
                    incident_penalty = max(incident_penalty, penalty)

                # "Worse of the two", never summed - an incident on an already-
                # congested road isn't more than maximally bad for routing purposes.
                cell_score = max(avg_congestion, incident_penalty)
                # Confidence-weighted effective score baked in here (CLAUDE.md traffic
                # master-prompt #16/#50) so app/optimization/fitness.py stays a
                # generic blender with no traffic-specific confidence logic of its own.
                matrix[i][j] = cell_score * avg_confidence

                confidences.append(avg_confidence)
                for r in usable:
                    statuses_seen.add(r.status)
                    if r.source:
                        sources_seen.add(r.source)
                    if r.updated_at and (latest_updated_at is None or r.updated_at > latest_updated_at):
                        latest_updated_at = r.updated_at

        if not confidences:
            return _baseline(size, enabled=True)

        status = TrafficStatus(
            enabled=True,
            available=True,
            status=_best(statuses_seen, _STATUS_PRIORITY) or "UNAVAILABLE",
            source=_best(sources_seen, _SOURCE_PRIORITY),
            confidence=sum(confidences) / len(confidences),
            updated_at=latest_updated_at,
        )
        return TrafficMatrixResult(matrix=matrix, status=status)

    async def _fetch_incidents(self, stops: list[Coordinate]) -> list:
        if self._tomtom_provider is None:
            return []
        try:
            west, south, east, north = build_bounding_box(stops, self._corridor_radius_meters)
            return await self._tomtom_provider.get_incidents(west, south, east, north)
        except TrafficProviderError:
            return []
