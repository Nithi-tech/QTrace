from fastapi import APIRouter, Depends

from app.api.deps import get_routing_provider
from app.routing.base import RoutingProvider
from app.schemas.routing import RouteRequest, RouteResult

router = APIRouter(prefix="/routes", tags=["routes"])


@router.post("", response_model=RouteResult)
async def compute_route(
    request: RouteRequest,
    routing_provider: RoutingProvider = Depends(get_routing_provider),
) -> RouteResult:
    """Plain road-network route with no optimization (CLAUDE.md #16 example: POST /api/v1/routes)."""
    return await routing_provider.route([request.origin, request.destination])
