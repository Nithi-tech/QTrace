package com.qtrace.app.data.api.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** Mirrors backend/app/schemas/traffic.py::TrafficSegmentFeature. */
@Serializable
data class TrafficSegmentFeatureDto(
    val id: String,
    val geometry: GeoJsonGeometryDto,
    @SerialName("current_speed_kph") val currentSpeedKph: Double,
    @SerialName("free_flow_speed_kph") val freeFlowSpeedKph: Double,
    @SerialName("speed_ratio") val speedRatio: Double,
    @SerialName("congestion_level") val congestionLevel: String,
    val confidence: Double? = null,
)

/** Mirrors backend/app/schemas/traffic.py::TrafficAreaResponse. */
@Serializable
data class TrafficAreaResponseDto(
    val enabled: Boolean,
    val status: String,
    val source: String? = null,
    @SerialName("updated_at") val updatedAt: String? = null,
    val segments: List<TrafficSegmentFeatureDto> = emptyList(),
)
