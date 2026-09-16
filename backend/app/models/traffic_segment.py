"""A road segment QTrace has observed traffic on, identified by the pair of OSM node
IDs it runs between (CLAUDE.md #7 domain model - road-network segment).

Node IDs come from OSRM's map-matching/nearest responses (app/routing/map_matching.py),
never invented - this is how QTrace stays city-independent without running its own
road graph (CLAUDE.md traffic-free-system master-prompt #35/#36).
"""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Float, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, new_uuid


class TrafficSegment(Base):
    __tablename__ = "traffic_segments"
    __table_args__ = (UniqueConstraint("node_a", "node_b", name="uq_traffic_segments_node_pair"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    # Always stored with node_a <= node_b so both travel directions map to one segment
    # (CLAUDE.md traffic-free-system master-prompt #21 - a documented simplification).
    node_a: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    node_b: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    geometry: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # GeoJSON LineString
    # OSRM's routing-profile speed for this edge (annotations=true "speed" field) -
    # NOT a verified OSM maxspeed tag (the public OSRM demo server does not expose
    # maxspeed annotations - see docs/TRAFFIC_ARCHITECTURE.md). This is tier 1 of the
    # reference-speed hierarchy in app/traffic/reference_speed.py.
    profile_speed_mps: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
