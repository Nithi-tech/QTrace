package com.qtrace.app.domain.repository

import com.qtrace.app.domain.model.FleetRouteRequest
import com.qtrace.app.domain.model.FleetRouteResult
import com.qtrace.app.domain.model.QTraceResult

interface FleetRepository {
    suspend fun planFleetRoutes(request: FleetRouteRequest): QTraceResult<FleetRouteResult>
}
