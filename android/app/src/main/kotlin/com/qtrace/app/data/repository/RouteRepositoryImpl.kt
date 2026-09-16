package com.qtrace.app.data.repository

import com.qtrace.app.data.api.QTraceApiService
import com.qtrace.app.data.api.dto.RouteRequestDto
import com.qtrace.app.domain.model.Coordinate
import com.qtrace.app.domain.model.OptimizationResult
import com.qtrace.app.domain.model.QTraceResult
import com.qtrace.app.domain.repository.RouteRepository
import kotlinx.coroutines.CancellationException
import kotlinx.serialization.json.Json
import javax.inject.Inject

class RouteRepositoryImpl @Inject constructor(
    private val api: QTraceApiService,
    private val json: Json,
) : RouteRepository {

    override suspend fun planRoute(origin: Coordinate, destination: Coordinate): QTraceResult<OptimizationResult> {
        val request = RouteRequestDto(origin = origin.toDto(), destination = destination.toDto())

        return try {
            val response = api.createOptimizationJob(request)
            val body = response.body()
            if (response.isSuccessful && body != null) {
                QTraceResult.Success(body.result.toDomain())
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
