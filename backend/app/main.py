"""FastAPI application entrypoint (CLAUDE.md #15, #16)."""

from fastapi import FastAPI

from app.core.config import get_settings
from app.schemas.health import HealthResponse


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", app_name=settings.app_name)

    # Versioned feature routers (app/api/v1/) are registered here as they land.

    return app


app = create_app()
