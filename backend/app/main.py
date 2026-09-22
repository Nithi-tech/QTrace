"""FastAPI application entrypoint (CLAUDE.md #15, #16)."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1.fleet import router as fleet_router
from app.api.v1.geocoding import router as geocoding_router
from app.api.v1.optimization import router as optimization_router
from app.api.v1.routes import router as routes_router
from app.api.v1.tracking import router as tracking_router
from app.api.v1.traffic import router as traffic_router
from app.core.config import get_settings
from app.geocoding.exceptions import (
    GeocodingConfigurationError,
    GeocodingProviderTimeoutError,
    GeocodingProviderUnavailableError,
)
from app.routing.exceptions import (
    InvalidRouteInputError,
    RoutingProviderTimeoutError,
    RoutingProviderUnavailableError,
    TooManyStopsError,
)
from app.schemas.errors import ErrorResponse
from app.schemas.health import HealthResponse
from app.services.exceptions import FleetInfeasibleError, TrackingSessionNotFoundError

logger = logging.getLogger(__name__)

# Domain exception -> (HTTP status, structured error code). Never leaks stack traces (CLAUDE.md #16, #19).
_ERROR_STATUS_MAP = {
    InvalidRouteInputError: 400,
    TooManyStopsError: 400,
    RoutingProviderTimeoutError: 504,
    RoutingProviderUnavailableError: 502,
    GeocodingConfigurationError: 503,
    GeocodingProviderTimeoutError: 504,
    GeocodingProviderUnavailableError: 502,
    FleetInfeasibleError: 422,
    TrackingSessionNotFoundError: 404,
}


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    for exc_type, status_code in _ERROR_STATUS_MAP.items():

        def make_handler(code: int):
            async def handler(request: Request, exc: Exception) -> JSONResponse:
                logger.warning("%s: %s", type(exc).__name__, exc)
                return JSONResponse(
                    status_code=code,
                    content=ErrorResponse(code=getattr(exc, "code", "ERROR"), message=str(exc)).model_dump(),
                )

            return handler

        app.add_exception_handler(exc_type, make_handler(status_code))

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", app_name=settings.app_name)

    app.include_router(routes_router, prefix=settings.api_v1_prefix)
    app.include_router(optimization_router, prefix=settings.api_v1_prefix)
    app.include_router(geocoding_router, prefix=settings.api_v1_prefix)
    app.include_router(fleet_router, prefix=settings.api_v1_prefix)
    app.include_router(tracking_router, prefix=settings.api_v1_prefix)
    app.include_router(traffic_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
