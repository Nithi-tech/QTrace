package com.qtrace.app.ui.screens.admin

import com.qtrace.app.domain.model.FleetTrackingOverview
import com.qtrace.app.domain.model.QTraceError

/** An administrator enters the planning_session_id shown after generating routes (see
 * ResultsStep) to see every vehicle from that run - live location, distance travelled, and
 * whether any have strayed off their planned route - on one map. */
data class AdminTrackingState(
    val jobIdInput: String = "",
    val isLoading: Boolean = false,
    val overview: FleetTrackingOverview? = null,
    val isPolling: Boolean = false,
    val error: QTraceError? = null,
) {
    val canLoad: Boolean get() = jobIdInput.isNotBlank() && !isLoading
}
