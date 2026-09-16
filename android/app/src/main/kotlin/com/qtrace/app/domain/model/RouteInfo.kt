package com.qtrace.app.domain.model

/** [geometry] is the ordered list of points to draw as the route polyline (decoded from the
 * backend's GeoJSON LineString) - empty when the provider returned no geometry. */
data class RouteInfo(
    val distanceMeters: Double,
    val durationSeconds: Double,
    val geometry: List<Coordinate>,
)
