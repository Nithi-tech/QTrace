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
from app.repositories.tracking_repository import TrackingRepository
from app.repositories.traffic_repository import TrafficRepository
from app.routing.base import RoutingProvider
from app.routing.map_matching import RoadMatchingProvider
from app.routing.osrm_provider import OSRMProvider
from app.services.fleet_optimization_service import FleetOptimizationService
from app.services.optimization_service import OptimizationService
from app.services.tracking_service import TrackingService
from app.traffic.area_sampler import TrafficAreaSampler
from app.traffic.cache import TTLCache
from app.traffic.matrix_service import TrafficMatrixService
from app.traffic.telemetry_service import TrafficTelemetryService
from app.traffic.tomtom_provider import TomTomTrafficProvider
from app.traffic.traffic_service import TrafficService

# Module-level, process-lifetime singletons (CLAUDE.md #73 - traffic responses are
# time-sensitive and cached in-process; a fresh cache per request would cache nothing).
_tomtom_flow_cache = TTLCache(ttl_seconds=get_settings().traffic_cache_ttl_seconds)


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


def get_matching_provider(settings: Settings = Depends(get_settings)) -> RoadMatchingProvider:
    """OSRMProvider implements both RoutingProvider and RoadMatchingProvider - kept as
    one instance-type, not a duplicate OSRM integration (CLAUDE.md traffic master-prompt
    forbids a second OSRM client)."""
    return OSRMProvider(
        base_url=settings.osrm_base_url,
        profile=settings.osrm_profile,
        timeout_seconds=settings.routing_request_timeout_seconds,
        max_retries=settings.routing_max_retries,
    )


def get_tomtom_traffic_provider(
    settings: Settings = Depends(get_settings),
) -> TomTomTrafficProvider | None:
    """None when no TOMTOM_API_KEY is configured - traffic then falls straight through
    to the QTrace crowd/historical tiers rather than failing the whole request
    (CLAUDE.md traffic master-prompt fallback hierarchy)."""
    if not settings.tomtom_api_key:
        return None
    return TomTomTrafficProvider(
        api_key=settings.tomtom_api_key,
        timeout_seconds=settings.traffic_timeout_seconds,
        max_retries=settings.traffic_max_retries,
    )


def get_traffic_repository(db: Session = Depends(get_db)) -> Generator[TrafficRepository, None, None]:
    yield TrafficRepository(db)


def get_traffic_service(
    tomtom_provider: TomTomTrafficProvider | None = Depends(get_tomtom_traffic_provider),
    matching_provider: RoadMatchingProvider = Depends(get_matching_provider),
    settings: Settings = Depends(get_settings),
) -> TrafficService:
    return TrafficService(
        tomtom_provider=tomtom_provider,
        matching_provider=matching_provider,
        cache=_tomtom_flow_cache,
        live_ttl_seconds=settings.traffic_live_ttl_seconds,
        recent_ttl_seconds=settings.traffic_recent_ttl_seconds,
        expired_seconds=settings.traffic_expired_seconds,
        min_observations=settings.traffic_min_observations,
    )


def get_traffic_matrix_service(
    traffic_service: TrafficService = Depends(get_traffic_service),
    tomtom_provider: TomTomTrafficProvider | None = Depends(get_tomtom_traffic_provider),
    settings: Settings = Depends(get_settings),
) -> TrafficMatrixService:
    return TrafficMatrixService(
        traffic_service=traffic_service,
        tomtom_provider=tomtom_provider,
        corridor_radius_meters=settings.traffic_corridor_radius_meters,
    )


def get_traffic_area_sampler(
    tomtom_provider: TomTomTrafficProvider | None = Depends(get_tomtom_traffic_provider),
    settings: Settings = Depends(get_settings),
) -> TrafficAreaSampler:
    """Shares _tomtom_flow_cache with get_traffic_service - a point already sampled for
    the map layer is instantly reused if QPSO/route-status resolves that same point (and
    vice versa), no separate cache instance needed (CLAUDE.md #46)."""
    return TrafficAreaSampler(
        tomtom_provider=tomtom_provider,
        cache=_tomtom_flow_cache,
        max_points=settings.traffic_area_max_points,
    )


def get_traffic_telemetry_service(
    matching_provider: RoadMatchingProvider = Depends(get_matching_provider),
    settings: Settings = Depends(get_settings),
) -> TrafficTelemetryService:
    return TrafficTelemetryService(
        matching_provider=matching_provider,
        min_observations=settings.traffic_min_observations,
        live_ttl_seconds=settings.traffic_live_ttl_seconds,
        recent_ttl_seconds=settings.traffic_recent_ttl_seconds,
        expired_seconds=settings.traffic_expired_seconds,
    )


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


def get_fleet_optimization_service(
    routing_provider: RoutingProvider = Depends(get_routing_provider),
    geocoding_provider: GeocodingProvider = Depends(get_geocoding_provider),
    job_repository: OptimizationJobRepository = Depends(get_optimization_job_repository),
) -> FleetOptimizationService:
    return FleetOptimizationService(
        routing_provider=routing_provider,
        geocoding_provider=geocoding_provider,
        job_repository=job_repository,
    )


def get_tracking_repository(db: Session = Depends(get_db)) -> Generator[TrackingRepository, None, None]:
    yield TrackingRepository(db)


def get_tracking_service(
    tracking_repository: TrackingRepository = Depends(get_tracking_repository),
) -> TrackingService:
    return TrackingService(tracking_repository)
