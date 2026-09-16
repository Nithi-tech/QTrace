package com.qtrace.app.domain.repository

import com.qtrace.app.domain.model.Coordinate
import com.qtrace.app.domain.model.OptimizationResult
import com.qtrace.app.domain.model.QTraceResult

interface RouteRepository {
    suspend fun planRoute(origin: Coordinate, destination: Coordinate): QTraceResult<OptimizationResult>
}
