"""Multi-vehicle fleet routing data contracts.

Additive to the existing single-vehicle RouteRequest/OptimizationRouteResult
(app/schemas/routing.py, app/schemas/optimization.py) - this module does not
change those, so the existing single-vehicle workflow (POST
/api/v1/optimization/jobs) keeps working unmodified.

Scope note: the per-vehicle route order is currently produced by a classical
nearest-neighbor + 2-Opt pass (app/optimization/greedy_route.py,
app/optimization/two_opt.py), not QPSO or the QISA design in
docs/qisa-roadmap.md - see app/services/fleet_optimization_service.py.
"""

from __future__ import annotations

import enum
from datetime import time

from pydantic import BaseModel, Field, model_validator

from app.schemas.routing import Coordinate


class ScenarioType(str, enum.Enum):
    PASSENGER_TRANSPORT = "PASSENGER_TRANSPORT"
    PACKAGE_DELIVERY = "PACKAGE_DELIVERY"
    GOODS_LOGISTICS = "GOODS_LOGISTICS"


class OptimizationObjective(str, enum.Enum):
    BALANCED = "BALANCED"
    MIN_TIME = "MIN_TIME"
    MIN_DISTANCE = "MIN_DISTANCE"
    MIN_COST = "MIN_COST"


class VehicleSpec(BaseModel):
    """One fleet entry: a vehicle type and how many of it are available."""

    vehicle_type: str = Field(min_length=1, description='e.g. "Van", "Mini Truck", "Bus".')
    count: int = Field(ge=1, description="Number of vehicles of this type available.")
    capacity: float = Field(
        gt=0, description="Max load per vehicle (kg, passengers, or units - scenario-defined)."
    )
    cost_per_km: float = Field(ge=0, default=0.0)
    availability_start: time | None = None
    availability_end: time | None = None


class Destination(BaseModel):
    """One delivery/pickup stop. Either `coordinate` or `address` must be given -
    `address` is resolved via GeocodingProvider when `coordinate` is absent
    (CLAUDE.md #38 - do not let invalid/incomplete input reach optimization)."""

    name: str = Field(min_length=1)
    address: str | None = None
    coordinate: Coordinate | None = None
    demand: float = Field(ge=0, default=0.0)
    time_window_start: time | None = None
    time_window_end: time | None = None
    service_time_seconds: int = Field(ge=0, default=0)

    @model_validator(mode="after")
    def _require_location(self) -> "Destination":
        if self.coordinate is None and not self.address:
            raise ValueError(f"Destination {self.name!r} needs either a coordinate or an address.")
        if self.time_window_start is not None and self.time_window_end is not None:
            if self.time_window_end <= self.time_window_start:
                raise ValueError(f"Destination {self.name!r} has time_window_end <= time_window_start.")
        return self


class FleetRouteRequest(BaseModel):
    scenario: ScenarioType
    depot: Coordinate
    return_to_depot: bool = True
    vehicles: list[VehicleSpec] = Field(min_length=1)
    destinations: list[Destination] = Field(min_length=1)
    objective: OptimizationObjective = OptimizationObjective.BALANCED


class VehicleRouteResult(BaseModel):
    vehicle_index: int = Field(description="0-based index identifying this vehicle instance in the response.")
    vehicle_type: str
    tracking_code: str | None = Field(
        default=None,
        description="Short code this vehicle's driver enters in the app to see their assigned "
        "route and report live location (POST /api/v1/tracking/{tracking_code}/ping).",
    )
    stop_names: list[str] = Field(
        description='Ordered visit list, e.g. ["Depot", "T Nagar", "Adyar", "Depot"].'
    )
    destination_indices: list[int] = Field(
        description="Indices into the request's `destinations` list, in visit order (excludes the depot)."
    )
    distance_meters: float
    duration_seconds: float
    load: float
    capacity: float
    capacity_utilization: float = Field(description="load / capacity, in [0, 1].")
    estimated_cost: float
    time_window_violations: list[str] = Field(default_factory=list)
    geometry: dict | None = None


class FleetRouteResponse(BaseModel):
    scenario: ScenarioType
    planning_session_id: str | None = Field(
        default=None,
        description="This planning run's id - pass it to GET /api/v1/tracking/jobs/{planning_session_id} "
        "for the admin fleet-wide tracking view of every vehicle generated here.",
    )
    objective: OptimizationObjective
    algorithm: str = Field(
        description="Per-vehicle route-ordering method actually used, e.g. 'GREEDY_NN_2OPT'."
    )
    is_feasible: bool = Field(
        description="False when one or more destinations could not be assigned to any vehicle."
    )
    infeasibility_reason: str | None = None
    vehicle_routes: list[VehicleRouteResult]
    unassigned_destination_indices: list[int] = Field(default_factory=list)
    total_distance_meters: float
    total_duration_seconds: float
    total_estimated_cost: float
    optimization_runtime_ms: float | None = None
