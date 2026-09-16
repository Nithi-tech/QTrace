package com.qtrace.app.data.api

import com.qtrace.app.data.api.dto.GeocodingSuggestionDto
import com.qtrace.app.data.api.dto.OptimizationJobResponseDto
import com.qtrace.app.data.api.dto.RouteRequestDto
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
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
}
