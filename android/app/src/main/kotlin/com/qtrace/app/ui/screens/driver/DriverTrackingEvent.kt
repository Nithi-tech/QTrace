package com.qtrace.app.ui.screens.driver

import com.qtrace.app.domain.model.Coordinate

sealed class DriverTrackingEvent {
    data class CodeInputChanged(val value: String) : DriverTrackingEvent()
    data object StartTrackingClicked : DriverTrackingEvent()
    data object RetryClicked : DriverTrackingEvent()
    data object ErrorDismissed : DriverTrackingEvent()
    data object StopTrackingClicked : DriverTrackingEvent()

    data class LocationPermissionResult(val granted: Boolean) : DriverTrackingEvent()
    data class LocationUpdated(val coordinate: Coordinate) : DriverTrackingEvent()
}
