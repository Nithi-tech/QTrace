package com.qtrace.app.domain.model

/** Mirrors backend/app/schemas/fleet.py::VehicleSpec. Availability times are "HH:MM" strings -
 * the backend's Pydantic `time` fields parse that format directly, so no client-side time
 * library is needed for this first version. */
data class VehicleSpec(
    val vehicleType: String,
    val count: Int,
    val capacity: Double,
    val costPerKm: Double,
    val availabilityStart: String? = null,
    val availabilityEnd: String? = null,
)

/** Mirrors backend/app/schemas/fleet.py::Destination. Either [coordinate] or [address] must be
 * set - the backend resolves [address] via its GeocodingProvider when [coordinate] is absent
 * (CLAUDE.md #38). */
data class FleetDestination(
    val name: String,
    val address: String? = null,
    val coordinate: Coordinate? = null,
    val demand: Double = 0.0,
    val timeWindowStart: String? = null,
    val timeWindowEnd: String? = null,
    val serviceTimeSeconds: Int = 0,
)

/** Mirrors backend/app/schemas/fleet.py::FleetRouteRequest. */
data class FleetRouteRequest(
    val scenario: ScenarioType,
    val depot: Coordinate,
    val returnToDepot: Boolean,
    val vehicles: List<VehicleSpec>,
    val destinations: List<FleetDestination>,
    val objective: OptimizationObjective,
)

/** Mirrors backend/app/schemas/fleet.py::VehicleRouteResult. */
data class VehicleRouteResult(
    val vehicleIndex: Int,
    val vehicleType: String,
    /** Code this vehicle's driver enters on the Drivers screen (see ui/screens/driver) to see
     * their assigned route and report live location. Null only if the backend didn't return one. */
    val trackingCode: String? = null,
    val stopNames: List<String>,
    val destinationIndices: List<Int>,
    val distanceMeters: Double,
    val durationSeconds: Double,
    val load: Double,
    val capacity: Double,
    val capacityUtilization: Double,
    val estimatedCost: Double,
    val timeWindowViolations: List<String>,
    val geometry: List<Coordinate>,
)

/** Mirrors backend/app/schemas/fleet.py::FleetRouteResponse. */
data class FleetRouteResult(
    val scenario: ScenarioType,
    /** This planning run's id - enter it on the Admin tracking screen (ui/screens/admin) to see
     * every vehicle generated here on one live map. Null only if the backend didn't return one. */
    val planningSessionId: String? = null,
    val objective: OptimizationObjective,
    val algorithm: String,
    val isFeasible: Boolean,
    val infeasibilityReason: String?,
    val vehicleRoutes: List<VehicleRouteResult>,
    val unassignedDestinationIndices: List<Int>,
    val totalDistanceMeters: Double,
    val totalDurationSeconds: Double,
    val totalEstimatedCost: Double,
)
