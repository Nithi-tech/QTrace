package com.qtrace.app.data.repository

import com.qtrace.app.data.api.QTraceApiService
import com.qtrace.app.data.api.dto.LocationPingRequestDto
import com.qtrace.app.domain.model.AssignedRoute
import com.qtrace.app.domain.model.Coordinate
import com.qtrace.app.domain.model.FleetTrackingOverview
import com.qtrace.app.domain.model.QTraceResult
import com.qtrace.app.domain.model.VehicleTrackingStatus
import com.qtrace.app.domain.repository.TrackingRepository
import kotlinx.coroutines.CancellationException
import kotlinx.serialization.json.Json
import javax.inject.Inject

class TrackingRepositoryImpl @Inject constructor(
    private val api: QTraceApiService,
    private val json: Json,
) : TrackingRepository {

    override suspend fun getAssignedRoute(trackingCode: String): QTraceResult<AssignedRoute> =
        safeCall { api.getAssignedRoute(trackingCode) }.map { it.toDomain() }

    override suspend fun postLocationPing(trackingCode: String, coordinate: Coordinate): QTraceResult<Unit> =
        try {
            val response = api.postLocationPing(trackingCode, LocationPingRequestDto(coordinate.toDto()))
            if (response.isSuccessful) {
                QTraceResult.Success(Unit)
            } else {
                QTraceResult.Failure(mapHttpErrorToQTraceError(response, json))
            }
        } catch (cancellation: CancellationException) {
            throw cancellation
        } catch (exception: Exception) {
            QTraceResult.Failure(mapThrowableToQTraceError(exception))
        }

    override suspend fun getStatus(trackingCode: String): QTraceResult<VehicleTrackingStatus> =
        safeCall { api.getTrackingStatus(trackingCode) }.map { it.toDomain() }

    override suspend fun getFleetOverview(jobId: String): QTraceResult<FleetTrackingOverview> =
        safeCall { api.getFleetTrackingOverview(jobId) }.map { it.toDomain() }

    private suspend fun <T> safeCall(call: suspend () -> retrofit2.Response<T>): QTraceResult<T> =
        try {
            val response = call()
            val body = response.body()
            if (response.isSuccessful && body != null) {
                QTraceResult.Success(body)
            } else {
                QTraceResult.Failure(mapHttpErrorToQTraceError(response, json))
            }
        } catch (cancellation: CancellationException) {
            throw cancellation
        } catch (exception: Exception) {
            QTraceResult.Failure(mapThrowableToQTraceError(exception))
        }

    private fun <T, R> QTraceResult<T>.map(transform: (T) -> R): QTraceResult<R> = when (this) {
        is QTraceResult.Success -> QTraceResult.Success(transform(data))
        is QTraceResult.Failure -> QTraceResult.Failure(error)
    }
}
