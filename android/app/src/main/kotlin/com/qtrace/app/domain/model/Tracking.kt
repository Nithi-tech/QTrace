package com.qtrace.app.domain.model

/** Mirrors backend/app/schemas/tracking.py::AssignedRoute - what a driver's app shows after
 * entering their tracking code. */
data class AssignedRoute(
    val trackingCode: String,
    val vehicleType: String,
    val stopNames: List<String>,
    val geometry: List<Coordinate>,
    val distanceMeters: Double,
    val durationSeconds: Double,
)

/** Mirrors backend/app/schemas/tracking.py::VehicleTrackingStatus - one vehicle's live status,
 * used by both the driver's own map and each entry in the admin's fleet-wide view. */
data class VehicleTrackingStatus(
    val trackingCode: String,
    val vehicleIndex: Int,
    val vehicleType: String,
    val stopNames: List<String>,
    val geometry: List<Coordinate>,
    val plannedDistanceMeters: Double,
    val currentLocation: Coordinate? = null,
    val lastPingAt: String? = null,
    val distanceTravelledMeters: Double = 0.0,
    val isOffRoute: Boolean = false,
    val offRouteDistanceMeters: Double? = null,
)

/** Mirrors backend/app/schemas/tracking.py::FleetTrackingOverview - the admin fleet-wide view. */
data class FleetTrackingOverview(
    val jobId: String,
    val vehicles: List<VehicleTrackingStatus>,
)
