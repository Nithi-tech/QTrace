from fastapi import APIRouter, Depends, Query

from app.api.deps import get_geocoding_provider
from app.geocoding.base import GeocodingProvider
from app.schemas.geocoding import GeocodingSuggestion

router = APIRouter(prefix="/geocoding", tags=["geocoding"])


@router.get("/search", response_model=list[GeocodingSuggestion])
async def search_locations(
    query: str = Query(min_length=1, max_length=200),
    limit: int = Query(default=5, ge=1, le=10),
    geocoding_provider: GeocodingProvider = Depends(get_geocoding_provider),
) -> list[GeocodingSuggestion]:
    return await geocoding_provider.search(query, limit=limit)
