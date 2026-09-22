package com.qtrace.app.ui.screens.fleetplanning

/**
 * Parses an uploaded destinations CSV (spec section 4). Expected header row, case-insensitive,
 * columns in any order: `name` (required), `demand`, `time_window_start`, `time_window_end`,
 * `service_time_minutes`, `latitude`, `longitude`, `address`.
 *
 * If `latitude`/`longitude` are absent, the row's `address` (or, failing that, its `name`) is
 * sent to the backend as-is and resolved via its existing GeocodingProvider - the app does not
 * geocode client-side (spec section 4: "If latitude/longitude are not provided, use the existing
 * geocoding functionality", which already lives server-side, see FleetOptimizationService).
 *
 * Deliberately a plain comma split, not a full RFC 4180 parser (no quoted-field/embedded-comma
 * support) - a known, stated simplification rather than adding a CSV library dependency for one
 * simple import screen (CLAUDE.md #32).
 */
class CsvParseException(message: String) : Exception(message)

object CsvDestinationParser {
    private val REQUIRED_COLUMNS = setOf("name")

    fun parse(csvContent: String): List<DestinationInput> {
        val lines = csvContent.lines().map { it.trim().trimEnd('\r') }.filter { it.isNotBlank() }
        if (lines.isEmpty()) throw CsvParseException("The file is empty.")

        val header = lines.first().split(",").map { it.trim().lowercase() }
        val columnIndex = header.withIndex().associate { (index, name) -> name to index }
        val missing = REQUIRED_COLUMNS - columnIndex.keys
        if (missing.isNotEmpty()) {
            throw CsvParseException("Missing required column(s): ${missing.joinToString(", ")}.")
        }

        return lines.drop(1).mapIndexed { rowIndex, line ->
            val cells = line.split(",").map { it.trim() }
            fun cell(column: String): String? = columnIndex[column]?.let { cells.getOrNull(it) }?.takeIf { it.isNotBlank() }

            val name = cell("name") ?: throw CsvParseException("Row ${rowIndex + 2}: missing a name.")
            val latitude = cell("latitude")?.toDoubleOrNull()
            val longitude = cell("longitude")?.toDoubleOrNull()
            val coordinate = if (latitude != null && longitude != null) {
                runCatching { com.qtrace.app.domain.model.Coordinate(latitude, longitude) }.getOrNull()
            } else {
                null
            }

            DestinationInput(
                query = name,
                name = name,
                address = if (coordinate == null) (cell("address") ?: name) else null,
                coordinate = coordinate,
                demand = cell("demand") ?: "0",
                timeWindowStart = cell("time_window_start") ?: "",
                timeWindowEnd = cell("time_window_end") ?: "",
                serviceTimeMinutes = cell("service_time_minutes") ?: "0",
            )
        }
    }
}
