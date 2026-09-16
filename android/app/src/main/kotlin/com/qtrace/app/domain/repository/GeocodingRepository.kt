package com.qtrace.app.domain.repository

import com.qtrace.app.domain.model.LocationSuggestion
import com.qtrace.app.domain.model.QTraceResult

interface GeocodingRepository {
    suspend fun search(query: String): QTraceResult<List<LocationSuggestion>>
}
