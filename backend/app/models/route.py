"""Route domain model (CLAUDE.md #7 - vehicle, ordered stops, geometry, distance, duration, cost, metadata)."""

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid


class Route(Base, TimestampMixin):
    __tablename__ = "routes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicles.id"), nullable=False)
    geometry: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    distance_meters: Mapped[float] = mapped_column(Float, nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    optimization_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    stops: Mapped[list["RouteStop"]] = relationship(
        back_populates="route", order_by="RouteStop.sequence", cascade="all, delete-orphan"
    )


class RouteStop(Base):
    """Ordered join between a route and its delivery stops."""

    __tablename__ = "route_stops"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    route_id: Mapped[str] = mapped_column(String(36), ForeignKey("routes.id"), nullable=False)
    delivery_stop_id: Mapped[str] = mapped_column(String(36), ForeignKey("delivery_stops.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    route: Mapped["Route"] = relationship(back_populates="stops")
