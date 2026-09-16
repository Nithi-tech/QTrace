package com.qtrace.app.data.repository

import com.qtrace.app.data.api.QTraceApiService
import com.qtrace.app.domain.model.FleetRouteRequest
import com.qtrace.app.domain.model.FleetRouteResult
import com.qtrace.app.domain.model.QTraceResult
import com.qtrace.app.domain.repository.FleetRepository
import kotlinx.coroutines.CancellationException
import kotlinx.serialization.json.Json
import javax.inject.Inject

class FleetRepositoryImpl @Inject constructor(
    private val api: QTraceApiService,
    private val json: Json,
) : FleetRepository {

    override suspend fun planFleetRoutes(request: FleetRouteRequest): QTraceResult<FleetRouteResult> {
        return try {
            val response = api.createFleetRoutes(request.toDto())
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
}
