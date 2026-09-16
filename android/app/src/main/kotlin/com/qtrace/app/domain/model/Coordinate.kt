package com.qtrace.app.domain.model

/**
 * Coordinate ordering convention (CLAUDE.md #39): QTrace uses (latitude, longitude)
 * everywhere - this class, the API DTOs, and the backend all agree on this order.
 * Never swap the two when constructing one.
 */
data class Coordinate(val latitude: Double, val longitude: Double) {
    init {
        require(latitude in -90.0..90.0) { "latitude must be within [-90, 90], was $latitude" }
        require(longitude in -180.0..180.0) { "longitude must be within [-180, 180], was $longitude" }
    }
}
