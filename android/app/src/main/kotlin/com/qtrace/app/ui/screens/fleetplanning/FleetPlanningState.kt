package com.qtrace.app.ui.screens.fleetplanning

import com.qtrace.app.domain.model.Coordinate
import com.qtrace.app.domain.model.FleetRouteResult
import com.qtrace.app.domain.model.LocationSuggestion
import com.qtrace.app.domain.model.OptimizationObjective
import com.qtrace.app.domain.model.QTraceError
import com.qtrace.app.domain.model.ScenarioType
import java.util.UUID

/** The user journey (spec section 12): Scenario -> Depot -> Fleet -> Destinations -> Review (map)
 * -> Results. Each step is a screen within the same wizard-style flow. */
enum class FleetPlanningStep { SCENARIO, DEPOT, FLEET, DESTINATIONS, REVIEW, RESULTS }

enum class VehicleField { TYPE, COUNT, CAPACITY, COST_PER_KM, AVAILABILITY_START, AVAILABILITY_END }
enum class DestinationField { NAME, DEMAND, TIME_WINDOW_START, TIME_WINDOW_END, SERVICE_TIME_MINUTES, LATITUDE, LONGITUDE }

/** A vehicle row being edited. Numeric fields are kept as raw strings while editing (Compose
 * TextField state) and parsed/validated only when checking [isValid] or submitting. */
data class VehicleSpecInput(
    val id: String = UUID.randomUUID().toString(),
    val vehicleType: String = "",
    val count: String = "1",
    val capacity: String = "",
    val costPerKm: String = "0",
    val availabilityStart: String = "",
    val availabilityEnd: String = "",
) {
    val isValid: Boolean
        get() = vehicleType.isNotBlank() &&
            (count.toIntOrNull() ?: 0) >= 1 &&
            (capacity.toDoubleOrNull() ?: 0.0) > 0.0
}

/** A destination row, either manually entered or parsed from an uploaded CSV. Either
 * [coordinate] or a non-blank [address] must end up set - the backend geocodes [address] when
 * [coordinate] is absent (CLAUDE.md #38), so a CSV row with only a place name still works by
 * using that name as the address. */
data class DestinationInput(
    val id: String = UUID.randomUUID().toString(),
    val name: String = "",
    val address: String? = null,
    val coordinate: Coordinate? = null,
    val latitude: String = "",
    val longitude: String = "",
    val demand: String = "0",
    val timeWindowStart: String = "",
    val timeWindowEnd: String = "",
    val serviceTimeMinutes: String = "0",
) {
    /** Explicit lat/lon typed in the UI take priority over [coordinate] (set by CSV import) -
     * either source, or a non-blank [address] for the backend to geocode, makes a row usable. */
    val effectiveCoordinate: Coordinate?
        get() = coordinate ?: run {
            val lat = latitude.toDoubleOrNull()
            val lon = longitude.toDoubleOrNull()
            if (lat != null && lon != null) runCatching { Coordinate(lat, lon) }.getOrNull() else null
        }

    val isValid: Boolean
        get() = name.isNotBlank() && (effectiveCoordinate != null || !address.isNullOrBlank())
}

data class FleetPlanningState(
    val step: FleetPlanningStep = FleetPlanningStep.SCENARIO,
    val scenario: ScenarioType? = null,

    val depotQuery: String = "",
    val depotSuggestions: List<LocationSuggestion> = emptyList(),
    val isSearchingDepot: Boolean = false,
    val depot: LocationSuggestion? = null,
    val returnToDepot: Boolean = true,

    val vehicles: List<VehicleSpecInput> = emptyList(),

    val destinations: List<DestinationInput> = emptyList(),
    val csvImportError: String? = null,

    val objective: OptimizationObjective = OptimizationObjective.BALANCED,

    val isSubmitting: Boolean = false,
    val result: FleetRouteResult? = null,

    val error: QTraceError? = null,
    val isOffline: Boolean = false,
) {
    val canProceedFromScenario: Boolean get() = scenario != null
    val canProceedFromDepot: Boolean get() = depot != null
    val canProceedFromFleet: Boolean get() = vehicles.isNotEmpty() && vehicles.all { it.isValid }
    val canProceedFromDestinations: Boolean get() = destinations.isNotEmpty() && destinations.all { it.isValid }

    val canGenerateRoutes: Boolean
        get() = !isSubmitting && !isOffline && depot != null && canProceedFromFleet && canProceedFromDestinations
}
