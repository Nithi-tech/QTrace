package com.qtrace.app.data.repository

import com.qtrace.app.data.api.dto.CoordinateDto
import com.qtrace.app.data.api.dto.GeoJsonGeometryDto
import com.qtrace.app.data.api.dto.GeocodingSuggestionDto
import com.qtrace.app.data.api.dto.OptimizationRouteResultDto
import com.qtrace.app.data.api.dto.RouteResultDto
import com.qtrace.app.domain.model.Coordinate
import com.qtrace.app.domain.model.LocationSuggestion
import com.qtrace.app.domain.model.OptimizationResult
import com.qtrace.app.domain.model.OptimizationStatus
import com.qtrace.app.domain.model.RouteInfo

fun CoordinateDto.toDomain(): Coordinate = Coordinate(latitude = latitude, longitude = longitude)

fun Coordinate.toDto(): CoordinateDto = CoordinateDto(latitude = latitude, longitude = longitude)

/**
 * GeoJSON coordinate pairs are [longitude, latitude] (GeoJSON spec) - the reverse of QTrace's
 * own (latitude, longitude) convention. This is the one place that conversion happens
 * (CLAUDE.md #39 - document conversions, never swap silently elsewhere).
 */
fun GeoJsonGeometryDto?.toCoordinateList(): List<Coordinate> =
    this?.coordinates.orEmpty().mapNotNull { pair ->
        if (pair.size < 2) return@mapNotNull null
        val (longitude, latitude) = pair[0] to pair[1]
        runCatching { Coordinate(latitude = latitude, longitude = longitude) }.getOrNull()
    }

fun RouteResultDto.toDomain(): RouteInfo =
    RouteInfo(
        distanceMeters = distanceMeters,
        durationSeconds = durationSeconds,
        geometry = geometry.toCoordinateList(),
    )

fun GeocodingSuggestionDto.toDomain(): LocationSuggestion =
    LocationSuggestion(label = label, coordinate = coordinate.toDomain())

fun OptimizationRouteResultDto.toDomain(): OptimizationResult =
    OptimizationResult(
        route = route.toDomain(),
        algorithm = algorithm,
        status = runCatching { OptimizationStatus.valueOf(status) }.getOrDefault(OptimizationStatus.FAILED),
        stopsCount = stopsCount,
        objectiveValue = objectiveValue,
        optimizationRuntimeMs = optimizationRuntimeMs,
        explanation = explanation,
    )
