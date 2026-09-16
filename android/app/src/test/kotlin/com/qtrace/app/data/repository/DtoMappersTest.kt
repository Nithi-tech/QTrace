package com.qtrace.app.data.repository

import com.qtrace.app.data.api.dto.CoordinateDto
import com.qtrace.app.data.api.dto.GeoJsonGeometryDto
import com.qtrace.app.data.api.dto.OptimizationRouteResultDto
import com.qtrace.app.data.api.dto.RouteResultDto
import com.qtrace.app.domain.model.OptimizationStatus
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class DtoMappersTest {

    @Test
    fun `GeoJSON lon-lat pairs are converted to lat-lon Coordinates`() {
        // GeoJSON order is [longitude, latitude] - the reverse of QTrace's domain convention.
        val geometry = GeoJsonGeometryDto(type = "LineString", coordinates = listOf(listOf(77.59, 12.97), listOf(77.60, 12.98)))

        val points = geometry.toCoordinateList()

        assertEquals(2, points.size)
        assertEquals(12.97, points[0].latitude, 0.0001)
        assertEquals(77.59, points[0].longitude, 0.0001)
        assertEquals(12.98, points[1].latitude, 0.0001)
        assertEquals(77.60, points[1].longitude, 0.0001)
    }

    @Test
    fun `null geometry maps to an empty coordinate list`() {
        assertTrue((null as GeoJsonGeometryDto?).toCoordinateList().isEmpty())
    }

    @Test
    fun `malformed coordinate pairs are skipped rather than crashing`() {
        val geometry = GeoJsonGeometryDto(type = "LineString", coordinates = listOf(listOf(77.59), listOf(77.60, 12.98)))

        val points = geometry.toCoordinateList()

        assertEquals(1, points.size)
    }

    @Test
    fun `unknown status string falls back to FAILED instead of throwing`() {
        val dto = OptimizationRouteResultDto(
            route = RouteResultDto(distanceMeters = 100.0, durationSeconds = 60.0),
            algorithm = "DIRECT_ROUTE",
            status = "SOMETHING_NEW",
            stopsCount = 2,
            explanation = "test",
        )

        assertEquals(OptimizationStatus.FAILED, dto.toDomain().status)
    }

    @Test
    fun `coordinate dto round trips through domain conversion`() {
        val dto = CoordinateDto(latitude = 12.97, longitude = 77.59)
        val domain = dto.toDomain()

        assertEquals(dto.latitude, domain.latitude, 0.0001)
        assertEquals(dto.longitude, domain.longitude, 0.0001)
        assertEquals(dto, domain.toDto())
    }
}
