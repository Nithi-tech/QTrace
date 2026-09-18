package com.qtrace.app.domain.model

/**
 * QTrace's own 5-level map-visualization classification (docs/TRAFFIC_ARCHITECTURE.md,
 * backend app/traffic/aggregation.py::classify_map_traffic_level) - a Google-Maps-style
 * scale, not Google's or any provider's thresholds. UNKNOWN is never colored on the map
 * (CLAUDE.md #12 - no traffic color without real data behind it).
 */
enum class TrafficLevel { FREE_FLOW, MODERATE, HEAVY, VERY_HEAVY, SEVERE, UNKNOWN }

fun trafficLevelFrom(raw: String?): TrafficLevel = when (raw) {
    "FREE_FLOW" -> TrafficLevel.FREE_FLOW
    "MODERATE" -> TrafficLevel.MODERATE
    "HEAVY" -> TrafficLevel.HEAVY
    "VERY_HEAVY" -> TrafficLevel.VERY_HEAVY
    "SEVERE" -> TrafficLevel.SEVERE
    else -> TrafficLevel.UNKNOWN
}

/**
 * One real, provider-returned road segment for the map traffic layer. [geometry] is
 * exactly what the backend reported - never a fabricated or straight-line shape
 * (CLAUDE.md traffic master-prompt #4).
 */
data class TrafficSegment(
    val id: String,
    val geometry: List<Coordinate>,
    val currentSpeedKph: Double,
    val freeFlowSpeedKph: Double,
    val speedRatio: Double,
    val level: TrafficLevel,
    val confidence: Double?,
)

/** Result of GET /api/v1/traffic/area - see TrafficStatus-style honesty rules: an empty/
 * unavailable result must never be presented as "no traffic" (i.e. free-flowing). */
data class TrafficAreaResult(
    val enabled: Boolean,
    val available: Boolean,
    val source: String?,
    val updatedAt: String?,
    val segments: List<TrafficSegment>,
)

/** A map viewport's visible geographic bounds - kept provider-agnostic (no MapLibre
 * LatLngBounds leaking into the domain/repository layers, CLAUDE.md #6.2/#6.3). */
data class MapBounds(
    val minLatitude: Double,
    val minLongitude: Double,
    val maxLatitude: Double,
    val maxLongitude: Double,
)
