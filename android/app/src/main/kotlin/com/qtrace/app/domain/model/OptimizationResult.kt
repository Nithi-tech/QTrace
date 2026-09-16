package com.qtrace.app.domain.model

enum class OptimizationStatus { QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED }

/**
 * [algorithm] is "DIRECT_ROUTE" for a plain two-point request (no stop order to optimize) or
 * "QPSO" once real optimization has run (CLAUDE.md #15, #67 - never claim optimization that
 * did not happen).
 */
data class OptimizationResult(
    val route: RouteInfo,
    val algorithm: String,
    val status: OptimizationStatus,
    val stopsCount: Int,
    val objectiveValue: Double?,
    val optimizationRuntimeMs: Double?,
    val explanation: String,
)
