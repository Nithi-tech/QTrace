package com.qtrace.app.ui.screens.routeplanning

import com.qtrace.app.domain.model.LocationSuggestion
import com.qtrace.app.domain.model.OptimizationResult
import com.qtrace.app.domain.model.QTraceError
import com.qtrace.app.domain.model.TrafficSegment

enum class ActiveSuggestionField { NONE, START, DESTINATION }

/** Google-Maps-style map traffic layer status (docs/TRAFFIC_ARCHITECTURE.md) - distinct
 * from [RoutePlanningState.error]: a failed/unavailable traffic layer never blocks route
 * planning or shows the screen-wide error banner (CLAUDE.md traffic master-prompt #34). */
enum class TrafficLayerStatus { OFF, LOADING, LIVE, UNAVAILABLE }

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

    val trafficEnabled: Boolean = false,
    val trafficLayerStatus: TrafficLayerStatus = TrafficLayerStatus.OFF,
    val trafficSegments: List<TrafficSegment> = emptyList(),
    val trafficSource: String? = null,
    val trafficUpdatedAt: String? = null,
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
