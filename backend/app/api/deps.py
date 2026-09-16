"""FastAPI dependency providers, wiring the provider abstractions into the API layer."""

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.geocoding.base import GeocodingProvider
from app.geocoding.tomtom_provider import TomTomGeocodingProvider
from app.repositories.optimization_job_repository import OptimizationJobRepository
from app.routing.base import RoutingProvider
from app.routing.osrm_provider import OSRMProvider
from app.services.optimization_service import OptimizationService


def get_routing_provider(settings: Settings = Depends(get_settings)) -> RoutingProvider:
    return OSRMProvider(
        base_url=settings.osrm_base_url,
        timeout_seconds=settings.routing_request_timeout_seconds,
        max_retries=settings.routing_max_retries,
    )


def get_geocoding_provider(settings: Settings = Depends(get_settings)) -> GeocodingProvider:
    return TomTomGeocodingProvider(
        api_key=settings.tomtom_api_key,
        timeout_seconds=settings.routing_request_timeout_seconds,
        max_retries=settings.routing_max_retries,
    )


def get_optimization_job_repository(
    db: Session = Depends(get_db),
) -> Generator[OptimizationJobRepository, None, None]:
    yield OptimizationJobRepository(db)


def get_optimization_service(
    routing_provider: RoutingProvider = Depends(get_routing_provider),
    job_repository: OptimizationJobRepository = Depends(get_optimization_job_repository),
) -> OptimizationService:
    return OptimizationService(routing_provider=routing_provider, job_repository=job_repository)
