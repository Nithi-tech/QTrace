package com.qtrace.app.data.repository

import com.qtrace.app.data.api.QTraceApiService
import com.qtrace.app.domain.model.MapBounds
import com.qtrace.app.domain.model.QTraceResult
import com.qtrace.app.domain.model.TrafficAreaResult
import com.qtrace.app.domain.repository.TrafficRepository
import kotlinx.coroutines.CancellationException
import kotlinx.serialization.json.Json
import javax.inject.Inject

class TrafficRepositoryImpl @Inject constructor(
    private val api: QTraceApiService,
    private val json: Json,
) : TrafficRepository {

    override suspend fun getTrafficArea(bounds: MapBounds): QTraceResult<TrafficAreaResult> = try {
        val response = api.getTrafficArea(
            minLat = bounds.minLatitude,
            minLon = bounds.minLongitude,
            maxLat = bounds.maxLatitude,
            maxLon = bounds.maxLongitude,
        )
        val body = response.body()
        if (response.isSuccessful && body != null) {
            QTraceResult.Success(body.toDomain())
        } else {
            QTraceResult.Failure(mapHttpErrorToQTraceError(response, json))
        }
    } catch (cancellation: CancellationException) {
        throw cancellation
    } catch (exception: Exception) {
        QTraceResult.Failure(mapThrowableToQTraceError(exception))
    }
}
