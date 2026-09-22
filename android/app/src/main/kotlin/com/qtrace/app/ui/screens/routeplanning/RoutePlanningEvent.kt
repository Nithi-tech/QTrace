package com.qtrace.app.ui.screens.routeplanning

import com.qtrace.app.domain.model.LocationSuggestion
import com.qtrace.app.domain.model.MapBounds

sealed class RoutePlanningEvent {
    data class StartQueryChanged(val query: String) : RoutePlanningEvent()
    data class DestinationQueryChanged(val query: String) : RoutePlanningEvent()
    data class StartLocationSelected(val suggestion: LocationSuggestion) : RoutePlanningEvent()
    data class DestinationLocationSelected(val suggestion: LocationSuggestion) : RoutePlanningEvent()
    data object StartFieldFocused : RoutePlanningEvent()
    data object DestinationFieldFocused : RoutePlanningEvent()
    data object SuggestionsDismissed : RoutePlanningEvent()
    data object ClearStartLocation : RoutePlanningEvent()
    data object ClearDestinationLocation : RoutePlanningEvent()
    data object OptimizeRouteClicked : RoutePlanningEvent()
    data object RetryClicked : RoutePlanningEvent()
    data object ErrorDismissed : RoutePlanningEvent()
    data object TrafficToggled : RoutePlanningEvent()
    data class MapBoundsChanged(val bounds: MapBounds) : RoutePlanningEvent()
}
