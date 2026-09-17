package com.qtrace.app.data.repository

import com.qtrace.app.data.api.dto.ErrorResponseDto
import com.qtrace.app.domain.model.QTraceError
import kotlinx.serialization.json.Json
import retrofit2.Response
import java.io.IOException
import java.net.SocketTimeoutException

/**
 * Maps a failed HTTP response's structured error code (CLAUDE.md #20 - ROUTING_PROVIDER_ERROR,
 * INVALID_ROUTE_INPUT, etc., see backend/app/schemas/errors.py) to a client-facing [QTraceError].
 * Never surfaces the raw response body to the UI (CLAUDE.md #16).
 */
fun mapHttpErrorToQTraceError(response: Response<*>, json: Json): QTraceError {
    val body = response.errorBody()?.string()
    val code = body?.let { runCatching { json.decodeFromString<ErrorResponseDto>(it).code }.getOrNull() }

    return when {
        code == "INVALID_ROUTE_INPUT" -> QTraceError.InvalidLocation
        code == "GEOCODING_PROVIDER_NOT_CONFIGURED" -> QTraceError.GeocodingFailed
        code == "GEOCODING_PROVIDER_UNAVAILABLE" -> QTraceError.GeocodingFailed
        code == "GEOCODING_PROVIDER_TIMEOUT" -> QTraceError.RequestTimedOut
        code == "ROUTING_PROVIDER_UNAVAILABLE" -> QTraceError.RoutingProviderUnavailable
        code == "ROUTING_PROVIDER_TIMEOUT" -> QTraceError.RequestTimedOut
        code == "FLEET_INFEASIBLE" -> QTraceError.OptimizationInfeasible
        code == "TRACKING_SESSION_NOT_FOUND" -> QTraceError.TrackingCodeNotFound
        response.code() == 404 -> QTraceError.Unknown("Not found")
        response.code() in 500..599 -> QTraceError.RoutingProviderUnavailable
        else -> QTraceError.Unknown(code ?: "HTTP ${response.code()}")
    }
}

/** Maps a network-layer exception (no response reached the server) to a [QTraceError]. */
fun mapThrowableToQTraceError(throwable: Throwable): QTraceError =
    when (throwable) {
        is SocketTimeoutException -> QTraceError.RequestTimedOut
        is IOException -> QTraceError.NetworkUnavailable
        else -> QTraceError.Unknown(throwable.message)
    }
