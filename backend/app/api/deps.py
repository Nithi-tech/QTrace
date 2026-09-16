"""FastAPI dependency providers, wiring the provider abstractions into the API layer."""

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.geocoding.base import GeocodingProvider
from app.geocoding.exceptions import GeocodingConfigurationError
from app.geocoding.nominatim_provider import NominatimProvider
from app.geocoding.tomtom_provider import TomTomGeocodingProvider
from app.optimization.fitness import FitnessWeights
from app.repositories.optimization_job_repository import OptimizationJobRepository
from app.repositories.traffic_repository import TrafficRepository
from app.routing.base import RoutingProvider
from app.routing.map_matching import RoadMatchingProvider
from app.routing.osrm_provider import OSRMProvider
from app.services.optimization_service import OptimizationService
from app.traffic.matrix_service import TrafficMatrixService
from app.traffic.service import TrafficTelemetryService


def _build_osrm_provider(settings: Settings) -> OSRMProvider:
    return OSRMProvider(
        base_url=settings.osrm_base_url,
        profile=settings.osrm_profile,
        timeout_seconds=settings.routing_request_timeout_seconds,
        max_retries=settings.routing_max_retries,
    )


def get_routing_provider(settings: Settings = Depends(get_settings)) -> RoutingProvider:
    return _build_osrm_provider(settings)


def get_road_matching_provider(settings: Settings = Depends(get_settings)) -> RoadMatchingProvider:
    """OSRMProvider implements both RoutingProvider and RoadMatchingProvider - see
    app/routing/map_matching.py for why these are kept as separate interfaces."""
    return _build_osrm_provider(settings)


def get_geocoding_provider(settings: Settings = Depends(get_settings)) -> GeocodingProvider:
    """Selects a GeocodingProvider by settings.geocoding_provider (CLAUDE.md #36 - explicit,
    never a silent runtime fallback between providers)."""
    if settings.geocoding_provider == "nominatim":
        return NominatimProvider(
            base_url=settings.nominatim_base_url,
            timeout_seconds=settings.routing_request_timeout_seconds,
            max_retries=settings.routing_max_retries,
        )
    if settings.geocoding_provider == "tomtom":
        return TomTomGeocodingProvider(
            api_key=settings.tomtom_api_key,
            timeout_seconds=settings.routing_request_timeout_seconds,
            max_retries=settings.routing_max_retries,
        )
    raise GeocodingConfigurationError(
        f"Unknown GEOCODING_PROVIDER {settings.geocoding_provider!r}; expected 'tomtom' or 'nominatim'."
    )


def get_optimization_job_repository(
    db: Session = Depends(get_db),
) -> Generator[OptimizationJobRepository, None, None]:
    yield OptimizationJobRepository(db)


def get_traffic_repository(db: Session = Depends(get_db)) -> Generator[TrafficRepository, None, None]:
    yield TrafficRepository(db)


def get_traffic_telemetry_service(
    matching_provider: RoadMatchingProvider = Depends(get_road_matching_provider),
    settings: Settings = Depends(get_settings),
) -> TrafficTelemetryService:
    return TrafficTelemetryService(
        matching_provider=matching_provider,
        min_observations=settings.traffic_min_observations,
        live_ttl_seconds=settings.traffic_live_ttl_seconds,
        recent_ttl_seconds=settings.traffic_recent_ttl_seconds,
        expired_seconds=settings.traffic_expired_seconds,
    )


def get_traffic_matrix_service(settings: Settings = Depends(get_settings)) -> TrafficMatrixService:
    return TrafficMatrixService(corridor_radius_meters=settings.traffic_corridor_radius_meters)


def get_optimization_service(
    routing_provider: RoutingProvider = Depends(get_routing_provider),
    job_repository: OptimizationJobRepository = Depends(get_optimization_job_repository),
    traffic_repository: TrafficRepository = Depends(get_traffic_repository),
    traffic_matrix_service: TrafficMatrixService = Depends(get_traffic_matrix_service),
    settings: Settings = Depends(get_settings),
) -> OptimizationService:
    return OptimizationService(
        routing_provider=routing_provider,
        job_repository=job_repository,
        max_stops=settings.max_route_stops,
        traffic_repository=traffic_repository,
        traffic_matrix_service=traffic_matrix_service,
        traffic_enabled=settings.traffic_enabled,
        fitness_weights=FitnessWeights(
            distance_weight=settings.distance_weight,
            time_weight=settings.time_weight,
            traffic_weight=settings.traffic_weight,
        ),
    )
