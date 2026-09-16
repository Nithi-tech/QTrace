package com.qtrace.app.data.api.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** Mirrors backend/app/schemas/routing.py::Coordinate - (latitude, longitude), same order. */
@Serializable
data class CoordinateDto(
    val latitude: Double,
    val longitude: Double,
)

/** Mirrors backend/app/schemas/routing.py::RouteRequest. */
@Serializable
data class RouteRequestDto(
    val origin: CoordinateDto,
    val destination: CoordinateDto,
)

/**
 * Mirrors backend/app/schemas/routing.py::RouteResult. [geometry] is raw GeoJSON, whose
 * coordinate pairs are [longitude, latitude] per the GeoJSON spec - the OPPOSITE of QTrace's own
 * (latitude, longitude) convention. That conversion happens only where this DTO is mapped to the
 * domain model (RouteMappers.kt), never silently elsewhere (CLAUDE.md #39).
 */
@Serializable
data class RouteResultDto(
    @SerialName("distance_meters") val distanceMeters: Double,
    @SerialName("duration_seconds") val durationSeconds: Double,
    val geometry: GeoJsonGeometryDto? = null,
)

@Serializable
data class GeoJsonGeometryDto(
    val type: String,
    val coordinates: List<List<Double>> = emptyList(),
)
