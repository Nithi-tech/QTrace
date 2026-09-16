"""Vehicle domain model (CLAUDE.md #7 - id, fleet_id, capacity, current location, operating constraints)."""

from sqlalchemy import JSON, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, new_uuid


class Vehicle(Base, TimestampMixin):
    __tablename__ = "vehicles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    fleet_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    capacity: Mapped[float] = mapped_column(Float, nullable=False)
    current_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    operating_constraints: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
