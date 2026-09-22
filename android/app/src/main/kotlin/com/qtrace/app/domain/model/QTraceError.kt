package com.qtrace.app.domain.model

/**
 * Structured, user-facing error categories (CLAUDE.md #20, #21). The UI maps each case to a
 * specific message (see RoutePlanningViewModel) rather than showing a raw exception (CLAUDE.md
 * #16 - never expose internal stack traces).
 */
sealed class QTraceError {
    data object NetworkUnavailable : QTraceError()
    data object GeocodingFailed : QTraceError()
    data object RoutingProviderUnavailable : QTraceError()
    data object OptimizationInfeasible : QTraceError()
    data object RequestTimedOut : QTraceError()
    data object SameLocation : QTraceError()
    data object InvalidLocation : QTraceError()
    data object TrackingCodeNotFound : QTraceError()
    data class Unknown(val message: String?) : QTraceError()
}
