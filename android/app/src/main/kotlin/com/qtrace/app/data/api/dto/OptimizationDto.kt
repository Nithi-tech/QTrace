package com.qtrace.app.data.api.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/** Mirrors backend/app/schemas/optimization.py::OptimizationRouteResult. */
@Serializable
data class OptimizationRouteResultDto(
    val route: RouteResultDto,
    val algorithm: String,
    val status: String,
    @SerialName("stops_count") val stopsCount: Int,
    @SerialName("objective_value") val objectiveValue: Double? = null,
    @SerialName("optimization_runtime_ms") val optimizationRuntimeMs: Double? = null,
    val explanation: String,
)

/** Mirrors backend/app/schemas/optimization.py::OptimizationJobResponse. */
@Serializable
data class OptimizationJobResponseDto(
    val id: String,
    val status: String,
    val algorithm: String,
    val result: OptimizationRouteResultDto,
    @SerialName("created_at") val createdAt: String,
)

/** Mirrors backend/app/schemas/errors.py::ErrorResponse - the JSON body on a 4xx/5xx response. */
@Serializable
data class ErrorResponseDto(
    val code: String,
    val message: String,
)
