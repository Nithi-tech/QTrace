package com.qtrace.app.data.repository

import com.qtrace.app.data.api.QTraceApiService
import com.qtrace.app.domain.model.LocationSuggestion
import com.qtrace.app.domain.model.QTraceResult
import com.qtrace.app.domain.repository.GeocodingRepository
import kotlinx.coroutines.CancellationException
import kotlinx.serialization.json.Json
import javax.inject.Inject

class GeocodingRepositoryImpl @Inject constructor(
    private val api: QTraceApiService,
    private val json: Json,
) : GeocodingRepository {

    override suspend fun search(query: String): QTraceResult<List<LocationSuggestion>> {
        if (query.isBlank()) return QTraceResult.Success(emptyList())

        return try {
            val response = api.searchLocations(query)
            val body = response.body()
            if (response.isSuccessful && body != null) {
                QTraceResult.Success(body.map { it.toDomain() })
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
