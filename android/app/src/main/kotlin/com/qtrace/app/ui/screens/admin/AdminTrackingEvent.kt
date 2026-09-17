package com.qtrace.app.ui.screens.admin

sealed class AdminTrackingEvent {
    data class JobIdInputChanged(val value: String) : AdminTrackingEvent()
    data object LoadClicked : AdminTrackingEvent()
    data object RetryClicked : AdminTrackingEvent()
    data object ErrorDismissed : AdminTrackingEvent()
    data object StopViewingClicked : AdminTrackingEvent()
}
