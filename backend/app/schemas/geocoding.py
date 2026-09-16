from pydantic import BaseModel

from app.schemas.routing import Coordinate


class GeocodingSuggestion(BaseModel):
    label: str  # human-readable address/place name, as returned by the provider
    coordinate: Coordinate
