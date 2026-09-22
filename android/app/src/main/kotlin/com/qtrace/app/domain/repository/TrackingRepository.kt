package com.qtrace.app.domain.repository

import com.qtrace.app.domain.model.AssignedRoute
import com.qtrace.app.domain.model.Coordinate
import com.qtrace.app.domain.model.FleetTrackingOverview
import com.qtrace.app.domain.model.QTraceResult
import com.qtrace.app.domain.model.VehicleTrackingStatus

interface TrackingRepository {
    /** Driver: the stops and route their tracking code was assigned. */
    suspend fun getAssignedRoute(trackingCode: String): QTraceResult<AssignedRoute>

    /** Driver: report their current location. */
    suspend fun postLocationPing(trackingCode: String, coordinate: Coordinate): QTraceResult<Unit>

    /** Driver: their own live status (current location, distance travelled so far). */
    suspend fun getStatus(trackingCode: String): QTraceResult<VehicleTrackingStatus>

    /** Admin: every vehicle from one planning run, with live status. */
    suspend fun getFleetOverview(jobId: String): QTraceResult<FleetTrackingOverview>
}
