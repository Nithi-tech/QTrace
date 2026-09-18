package com.qtrace.app.domain.model

enum class OptimizationStatus { QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED }

/**
 * What the backend's TomTom live -> QTrace crowd -> historical -> unavailable fallback
 * hierarchy actually resolved for this request (docs/TRAFFIC_ARCHITECTURE.md). [status] is
 * one of "LIVE"/"RECENT"/"STALE"/"HISTORICAL"/"UNAVAILABLE"; [source] is one of
 * "TOMTOM"/"QTRACE_CROWD"/"HISTORICAL", or null when [available] is false. [level] is QTrace's
 * own congestion classification for this specific route ("LOW"/"MODERATE"/"HEAVY", or null when
 * unavailable) - not any provider's label (app/traffic/aggregation.py::classify_traffic_level).
 * Never fabricated - this mirrors exactly what the backend measured (CLAUDE.md #12, #43).
 */
data class TrafficInfo(
    val enabled: Boolean,
    val available: Boolean,
    val status: String,
    val source: String?,
    val confidence: Double?,
    val level: String?,
)

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
    val traffic: TrafficInfo,
    val trafficImpactSeconds: Double?,
)
