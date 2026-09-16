package com.qtrace.app.data.repository

import com.qtrace.app.domain.model.QTraceError
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import retrofit2.Response
import java.io.IOException
import java.net.SocketTimeoutException

class ApiErrorMapperTest {

    private val json = Json { ignoreUnknownKeys = true }

    private fun errorResponse(code: Int, errorCode: String): Response<Unit> {
        val body = """{"code":"$errorCode","message":"details"}"""
        return Response.error(code, body.toResponseBody("application/json".toMediaType()))
    }

    @Test
    fun `maps INVALID_ROUTE_INPUT to InvalidLocation`() {
        assertEquals(QTraceError.InvalidLocation, mapHttpErrorToQTraceError(errorResponse(400, "INVALID_ROUTE_INPUT"), json))
    }

    @Test
    fun `maps ROUTING_PROVIDER_UNAVAILABLE to RoutingProviderUnavailable`() {
        val error = mapHttpErrorToQTraceError(errorResponse(502, "ROUTING_PROVIDER_UNAVAILABLE"), json)
        assertEquals(QTraceError.RoutingProviderUnavailable, error)
    }

    @Test
    fun `maps ROUTING_PROVIDER_TIMEOUT to RequestTimedOut`() {
        assertEquals(QTraceError.RequestTimedOut, mapHttpErrorToQTraceError(errorResponse(504, "ROUTING_PROVIDER_TIMEOUT"), json))
    }

    @Test
    fun `maps GEOCODING_PROVIDER_NOT_CONFIGURED to GeocodingFailed`() {
        val error = mapHttpErrorToQTraceError(errorResponse(503, "GEOCODING_PROVIDER_NOT_CONFIGURED"), json)
        assertEquals(QTraceError.GeocodingFailed, error)
    }

    @Test
    fun `unrecognized 4xx error code falls back to Unknown, never crashes`() {
        val error = mapHttpErrorToQTraceError(errorResponse(422, "SOME_NEW_CODE"), json)
        assertTrue(error is QTraceError.Unknown)
    }

    @Test
    fun `unrecognized 5xx error is treated as a provider outage, not a raw unknown`() {
        val error = mapHttpErrorToQTraceError(errorResponse(500, "SOME_NEW_CODE"), json)
        assertEquals(QTraceError.RoutingProviderUnavailable, error)
    }

    @Test
    fun `IOException maps to NetworkUnavailable`() {
        assertEquals(QTraceError.NetworkUnavailable, mapThrowableToQTraceError(IOException("no connection")))
    }

    @Test
    fun `SocketTimeoutException maps to RequestTimedOut`() {
        assertEquals(QTraceError.RequestTimedOut, mapThrowableToQTraceError(SocketTimeoutException("timed out")))
    }
}
