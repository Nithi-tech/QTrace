package com.qtrace.app.ui.screens.routeplanning

import com.qtrace.app.domain.model.LocationSuggestion
import com.qtrace.app.domain.model.OptimizationResult
import com.qtrace.app.domain.model.QTraceError

enum class ActiveSuggestionField { NONE, START, DESTINATION }

/**
 * Immutable UI state for the route-planning screen (CLAUDE.md #25). A single source of truth;
 * the ViewModel is the only thing that produces a new instance.
 */
data class RoutePlanningState(
    val startQuery: String = "",
    val startSuggestions: List<LocationSuggestion> = emptyList(),
    val isSearchingStart: Boolean = false,
    val startLocation: LocationSuggestion? = null,

    val destinationQuery: String = "",
    val destinationSuggestions: List<LocationSuggestion> = emptyList(),
    val isSearchingDestination: Boolean = false,
    val destinationLocation: LocationSuggestion? = null,

    val activeSuggestionField: ActiveSuggestionField = ActiveSuggestionField.NONE,

    val isPlanningRoute: Boolean = false,
    val optimizationResult: OptimizationResult? = null,

    val error: QTraceError? = null,
    val isOffline: Boolean = false,
) {
    val isSameLocationSelected: Boolean
        get() = startLocation != null && destinationLocation != null &&
            startLocation.coordinate == destinationLocation.coordinate

    val canOptimize: Boolean
        get() = startLocation != null &&
            destinationLocation != null &&
            !isSameLocationSelected &&
            !isPlanningRoute &&
            !isOffline
}
