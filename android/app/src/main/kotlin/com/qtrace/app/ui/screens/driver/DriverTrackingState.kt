package com.qtrace.app.ui.screens.driver

import com.qtrace.app.domain.model.AssignedRoute
import com.qtrace.app.domain.model.Coordinate
import com.qtrace.app.domain.model.QTraceError

enum class DriverTrackingStep { CODE_ENTRY, TRACKING }

/** A driver enters their tracking code (given to them after route generation, see
 * ResultsStep's per-vehicle code) to see their assigned stops on a map and start reporting
 * their live location - the whole point of the Drivers page. */
data class DriverTrackingState(
    val step: DriverTrackingStep = DriverTrackingStep.CODE_ENTRY,
    val codeInput: String = "",
    val isLoading: Boolean = false,
    val assignedRoute: AssignedRoute? = null,
    val locationPermissionGranted: Boolean = false,
    val currentLocation: Coordinate? = null,
    val distanceTravelledMeters: Double = 0.0,
    val lastPingFailed: Boolean = false,
    val error: QTraceError? = null,
) {
    val canStartTracking: Boolean get() = codeInput.isNotBlank() && !isLoading
}
