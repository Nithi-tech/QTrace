package com.qtrace.app.data.api.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** Mirrors backend/app/schemas/fleet.py::VehicleSpec. */
@Serializable
data class VehicleSpecDto(
    @SerialName("vehicle_type") val vehicleType: String,
    val count: Int,
    val capacity: Double,
    @SerialName("cost_per_km") val costPerKm: Double,
    @SerialName("availability_start") val availabilityStart: String? = null,
    @SerialName("availability_end") val availabilityEnd: String? = null,
)

/** Mirrors backend/app/schemas/fleet.py::Destination. */
@Serializable
data class DestinationDto(
    val name: String,
    val address: String? = null,
    val coordinate: CoordinateDto? = null,
    val demand: Double = 0.0,
    @SerialName("time_window_start") val timeWindowStart: String? = null,
    @SerialName("time_window_end") val timeWindowEnd: String? = null,
    @SerialName("service_time_seconds") val serviceTimeSeconds: Int = 0,
)

/** Mirrors backend/app/schemas/fleet.py::FleetRouteRequest. */
@Serializable
data class FleetRouteRequestDto(
    val scenario: String,
    val depot: CoordinateDto,
    @SerialName("return_to_depot") val returnToDepot: Boolean,
    val vehicles: List<VehicleSpecDto>,
    val destinations: List<DestinationDto>,
    val objective: String,
)

/** Mirrors backend/app/schemas/fleet.py::VehicleRouteResult. */
@Serializable
data class VehicleRouteResultDto(
    @SerialName("vehicle_index") val vehicleIndex: Int,
    @SerialName("vehicle_type") val vehicleType: String,
    @SerialName("tracking_code") val trackingCode: String? = null,
    @SerialName("stop_names") val stopNames: List<String>,
    @SerialName("destination_indices") val destinationIndices: List<Int>,
    @SerialName("distance_meters") val distanceMeters: Double,
    @SerialName("duration_seconds") val durationSeconds: Double,
    val load: Double,
    val capacity: Double,
    @SerialName("capacity_utilization") val capacityUtilization: Double,
    @SerialName("estimated_cost") val estimatedCost: Double,
    @SerialName("time_window_violations") val timeWindowViolations: List<String> = emptyList(),
    val geometry: GeoJsonGeometryDto? = null,
)

/** Mirrors backend/app/schemas/fleet.py::FleetRouteResponse. */
@Serializable
data class FleetRouteResponseDto(
    val scenario: String,
    @SerialName("planning_session_id") val planningSessionId: String? = null,
    val objective: String,
    val algorithm: String,
    @SerialName("is_feasible") val isFeasible: Boolean,
    @SerialName("infeasibility_reason") val infeasibilityReason: String? = null,
    @SerialName("vehicle_routes") val vehicleRoutes: List<VehicleRouteResultDto>,
    @SerialName("unassigned_destination_indices") val unassignedDestinationIndices: List<Int> = emptyList(),
    @SerialName("total_distance_meters") val totalDistanceMeters: Double,
    @SerialName("total_duration_seconds") val totalDurationSeconds: Double,
    @SerialName("total_estimated_cost") val totalEstimatedCost: Double,
)
