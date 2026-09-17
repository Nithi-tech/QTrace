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
enum class DestinationField { DEMAND, TIME_WINDOW_START, TIME_WINDOW_END, SERVICE_TIME_MINUTES }

/** A vehicle row being edited. Numeric fields are kept as raw strings while editing (Compose
 * TextField state) and parsed/validated only when checking [isValid] or submitting. */
data class VehicleSpecInput(
    val id: String = UUID.randomUUID().toString(),
    val vehicleType: String = "",
    val count: String = "",
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

/**
 * A destination row. [query] drives a live geocoding search exactly like the depot field
 * (LocationSearchField) - the user picks a real suggestion, which sets [name]/[coordinate]
 * together, so the location is *confirmed* rather than a bare name guessed at by the backend
 * at submit time. This is what fixes "the name alone can't correctly determine [the place]":
 * previously a destination was just free text sent straight to the backend's geocoder with no
 * feedback if it picked the wrong (or no) result.
 *
 * A row can still end up with only [address] set and no [coordinate] - e.g. a CSV-imported row
 * with just a name and no lat/lon column - in which case the backend geocodes it server-side as
 * a fallback (CLAUDE.md #38); [isConfirmed] is false in that case so the UI can flag it.
 */
data class DestinationInput(
    val id: String = UUID.randomUUID().toString(),
    val query: String = "",
    val suggestions: List<LocationSuggestion> = emptyList(),
    val isSearching: Boolean = false,
    val name: String = "",
    val address: String? = null,
    val coordinate: Coordinate? = null,
    val demand: String = "0",
    val timeWindowStart: String = "",
    val timeWindowEnd: String = "",
    val serviceTimeMinutes: String = "0",
) {
    /** True once this row has a real coordinate behind it (search-confirmed, manually entered
     * via [com.qtrace.app.ui.components.ManualCoordinateEntry], or from a CSV lat/lon column) -
     * not just a name hoping the backend can resolve it. */
    val isConfirmed: Boolean
        get() = coordinate != null

    val isValid: Boolean
        get() = name.isNotBlank() && (isConfirmed || !address.isNullOrBlank())
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
