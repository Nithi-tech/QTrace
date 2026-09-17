package com.qtrace.app.data.api.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** Mirrors backend/app/schemas/tracking.py::LocationPingRequest. */
@Serializable
data class LocationPingRequestDto(val coordinate: CoordinateDto)

/** Mirrors backend/app/schemas/tracking.py::AssignedRoute. Note: `geometry` here is a plain list
 * of {latitude, longitude} points (already parsed server-side), unlike FleetDto's
 * GeoJsonGeometryDto - the tracking endpoints don't return raw GeoJSON. */
@Serializable
data class AssignedRouteDto(
    @SerialName("tracking_code") val trackingCode: String,
    @SerialName("vehicle_type") val vehicleType: String,
    @SerialName("stop_names") val stopNames: List<String>,
    val geometry: List<CoordinateDto>,
    @SerialName("distance_meters") val distanceMeters: Double,
    @SerialName("duration_seconds") val durationSeconds: Double,
)

/** Mirrors backend/app/schemas/tracking.py::VehicleTrackingStatus. */
@Serializable
data class VehicleTrackingStatusDto(
    @SerialName("tracking_code") val trackingCode: String,
    @SerialName("vehicle_index") val vehicleIndex: Int,
    @SerialName("vehicle_type") val vehicleType: String,
    @SerialName("stop_names") val stopNames: List<String>,
    val geometry: List<CoordinateDto>,
    @SerialName("planned_distance_meters") val plannedDistanceMeters: Double,
    @SerialName("current_location") val currentLocation: CoordinateDto? = null,
    @SerialName("last_ping_at") val lastPingAt: String? = null,
    @SerialName("distance_travelled_meters") val distanceTravelledMeters: Double = 0.0,
    @SerialName("is_off_route") val isOffRoute: Boolean = false,
    @SerialName("off_route_distance_meters") val offRouteDistanceMeters: Double? = null,
)

/** Mirrors backend/app/schemas/tracking.py::FleetTrackingOverview. */
@Serializable
data class FleetTrackingOverviewDto(
    @SerialName("job_id") val jobId: String,
    val vehicles: List<VehicleTrackingStatusDto>,
)
