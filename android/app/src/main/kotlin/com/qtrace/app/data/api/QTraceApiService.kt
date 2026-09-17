package com.qtrace.app.data.api

import com.qtrace.app.data.api.dto.AssignedRouteDto
import com.qtrace.app.data.api.dto.FleetRouteRequestDto
import com.qtrace.app.data.api.dto.FleetRouteResponseDto
import com.qtrace.app.data.api.dto.FleetTrackingOverviewDto
import com.qtrace.app.data.api.dto.GeocodingSuggestionDto
import com.qtrace.app.data.api.dto.LocationPingRequestDto
import com.qtrace.app.data.api.dto.OptimizationJobResponseDto
import com.qtrace.app.data.api.dto.RouteRequestDto
import com.qtrace.app.data.api.dto.VehicleTrackingStatusDto
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

/** Matches the backend's versioned REST surface (CLAUDE.md #16). */
interface QTraceApiService {

    @GET("api/v1/geocoding/search")
    suspend fun searchLocations(
        @Query("query") query: String,
        @Query("limit") limit: Int = 5,
    ): Response<List<GeocodingSuggestionDto>>

    @POST("api/v1/optimization/jobs")
    suspend fun createOptimizationJob(@Body request: RouteRequestDto): Response<OptimizationJobResponseDto>

    @POST("api/v1/fleet/routes")
    suspend fun createFleetRoutes(@Body request: FleetRouteRequestDto): Response<FleetRouteResponseDto>

    @GET("api/v1/tracking/{trackingCode}")
    suspend fun getAssignedRoute(@Path("trackingCode") trackingCode: String): Response<AssignedRouteDto>

    @POST("api/v1/tracking/{trackingCode}/ping")
    suspend fun postLocationPing(
        @Path("trackingCode") trackingCode: String,
        @Body request: LocationPingRequestDto,
    ): Response<Unit>

    @GET("api/v1/tracking/{trackingCode}/status")
    suspend fun getTrackingStatus(@Path("trackingCode") trackingCode: String): Response<VehicleTrackingStatusDto>

    @GET("api/v1/tracking/jobs/{jobId}")
    suspend fun getFleetTrackingOverview(@Path("jobId") jobId: String): Response<FleetTrackingOverviewDto>
}
