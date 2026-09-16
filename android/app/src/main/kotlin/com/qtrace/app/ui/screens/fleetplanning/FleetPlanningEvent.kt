package com.qtrace.app.ui.screens.fleetplanning

import com.qtrace.app.domain.model.LocationSuggestion
import com.qtrace.app.domain.model.OptimizationObjective
import com.qtrace.app.domain.model.ScenarioType

sealed class FleetPlanningEvent {
    data class ScenarioSelected(val scenario: ScenarioType) : FleetPlanningEvent()

    data class DepotQueryChanged(val query: String) : FleetPlanningEvent()
    data object DepotFieldFocused : FleetPlanningEvent()
    data object DepotSuggestionsDismissed : FleetPlanningEvent()
    data class DepotSelected(val suggestion: LocationSuggestion) : FleetPlanningEvent()
    data object ClearDepot : FleetPlanningEvent()
    data class ReturnToDepotToggled(val value: Boolean) : FleetPlanningEvent()

    data object AddVehicle : FleetPlanningEvent()
    data class RemoveVehicle(val id: String) : FleetPlanningEvent()
    data class VehicleFieldChanged(val id: String, val field: VehicleField, val value: String) : FleetPlanningEvent()

    data object AddDestination : FleetPlanningEvent()
    data class RemoveDestination(val id: String) : FleetPlanningEvent()
    data class DestinationFieldChanged(val id: String, val field: DestinationField, val value: String) :
        FleetPlanningEvent()
    data class CsvImported(val csvContent: String) : FleetPlanningEvent()
    data object CsvImportErrorDismissed : FleetPlanningEvent()

    data class ObjectiveSelected(val objective: OptimizationObjective) : FleetPlanningEvent()

    data object NextStepClicked : FleetPlanningEvent()
    data object BackStepClicked : FleetPlanningEvent()
    data object GenerateRoutesClicked : FleetPlanningEvent()
    data object RetryClicked : FleetPlanningEvent()
    data object ErrorDismissed : FleetPlanningEvent()
    data object StartOverClicked : FleetPlanningEvent()
}
