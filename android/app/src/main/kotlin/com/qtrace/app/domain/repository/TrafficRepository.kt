package com.qtrace.app.domain.repository

import com.qtrace.app.domain.model.MapBounds
import com.qtrace.app.domain.model.QTraceResult
import com.qtrace.app.domain.model.TrafficAreaResult

interface TrafficRepository {
    suspend fun getTrafficArea(bounds: MapBounds): QTraceResult<TrafficAreaResult>
}
