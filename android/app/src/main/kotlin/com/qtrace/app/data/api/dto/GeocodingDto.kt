package com.qtrace.app.data.api.dto

import kotlinx.serialization.Serializable

/** Mirrors backend/app/schemas/geocoding.py::GeocodingSuggestion. */
@Serializable
data class GeocodingSuggestionDto(
    val label: String,
    val coordinate: CoordinateDto,
)
