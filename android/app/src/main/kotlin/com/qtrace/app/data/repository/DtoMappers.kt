package com.qtrace.app.data.repository

import com.qtrace.app.data.api.dto.CoordinateDto
import com.qtrace.app.data.api.dto.DestinationDto
import com.qtrace.app.data.api.dto.FleetRouteRequestDto
import com.qtrace.app.data.api.dto.FleetRouteResponseDto
import com.qtrace.app.data.api.dto.GeoJsonGeometryDto
import com.qtrace.app.data.api.dto.GeocodingSuggestionDto
import com.qtrace.app.data.api.dto.OptimizationRouteResultDto
import com.qtrace.app.data.api.dto.RouteResultDto
import com.qtrace.app.data.api.dto.VehicleRouteResultDto
import com.qtrace.app.data.api.dto.VehicleSpecDto
import com.qtrace.app.domain.model.Coordinate
import com.qtrace.app.domain.model.FleetDestination
import com.qtrace.app.domain.model.FleetRouteRequest
import com.qtrace.app.domain.model.FleetRouteResult
import com.qtrace.app.domain.model.LocationSuggestion
import com.qtrace.app.domain.model.OptimizationObjective
import com.qtrace.app.domain.model.OptimizationResult
import com.qtrace.app.domain.model.OptimizationStatus
import com.qtrace.app.domain.model.RouteInfo
import com.qtrace.app.domain.model.ScenarioType
import com.qtrace.app.domain.model.VehicleRouteResult
import com.qtrace.app.domain.model.VehicleSpec

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

fun VehicleSpec.toDto(): VehicleSpecDto =
    VehicleSpecDto(
        vehicleType = vehicleType,
        count = count,
        capacity = capacity,
        costPerKm = costPerKm,
        availabilityStart = availabilityStart,
        availabilityEnd = availabilityEnd,
    )

fun FleetDestination.toDto(): DestinationDto =
    DestinationDto(
        name = name,
        address = address,
        coordinate = coordinate?.toDto(),
        demand = demand,
        timeWindowStart = timeWindowStart,
        timeWindowEnd = timeWindowEnd,
        serviceTimeSeconds = serviceTimeSeconds,
    )

fun FleetRouteRequest.toDto(): FleetRouteRequestDto =
    FleetRouteRequestDto(
        scenario = scenario.name,
        depot = depot.toDto(),
        returnToDepot = returnToDepot,
        vehicles = vehicles.map { it.toDto() },
        destinations = destinations.map { it.toDto() },
        objective = objective.name,
    )

fun VehicleRouteResultDto.toDomain(): VehicleRouteResult =
    VehicleRouteResult(
        vehicleIndex = vehicleIndex,
        vehicleType = vehicleType,
        stopNames = stopNames,
        destinationIndices = destinationIndices,
        distanceMeters = distanceMeters,
        durationSeconds = durationSeconds,
        load = load,
        capacity = capacity,
        capacityUtilization = capacityUtilization,
        estimatedCost = estimatedCost,
        timeWindowViolations = timeWindowViolations,
        geometry = geometry.toCoordinateList(),
    )

fun FleetRouteResponseDto.toDomain(): FleetRouteResult =
    FleetRouteResult(
        scenario = runCatching { ScenarioType.valueOf(scenario) }.getOrDefault(ScenarioType.GOODS_LOGISTICS),
        objective = runCatching { OptimizationObjective.valueOf(objective) }.getOrDefault(OptimizationObjective.BALANCED),
        algorithm = algorithm,
        isFeasible = isFeasible,
        infeasibilityReason = infeasibilityReason,
        vehicleRoutes = vehicleRoutes.map { it.toDomain() },
        unassignedDestinationIndices = unassignedDestinationIndices,
        totalDistanceMeters = totalDistanceMeters,
        totalDurationSeconds = totalDurationSeconds,
        totalEstimatedCost = totalEstimatedCost,
    )
