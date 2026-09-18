package com.qtrace.app.ui.screens.routeplanning

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.qtrace.app.data.network.ConnectivityObserver
import com.qtrace.app.domain.model.LocationSuggestion
import com.qtrace.app.domain.model.MapBounds
import com.qtrace.app.domain.model.QTraceResult
import com.qtrace.app.domain.repository.GeocodingRepository
import com.qtrace.app.domain.repository.RouteRepository
import com.qtrace.app.domain.repository.TrafficRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.debounce
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.filter
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject
import kotlin.math.abs

private const val SEARCH_DEBOUNCE_MS = 350L
private const val MIN_QUERY_LENGTH = 2
private const val TRAFFIC_DEBOUNCE_MS = 600L

/** Skips a re-fetch for a camera move that barely changed the visible area - only a
 * pan/zoom that shifts the viewport by more than 20% of its own span triggers a new
 * traffic request (CLAUDE.md traffic master-prompt #18/#19/#33). */
private fun isSignificantBoundsChange(old: MapBounds, new: MapBounds): Boolean {
    val latSpan = (old.maxLatitude - old.minLatitude).coerceAtLeast(1e-6)
    val lonSpan = (old.maxLongitude - old.minLongitude).coerceAtLeast(1e-6)
    val latDelta = abs(new.minLatitude - old.minLatitude) + abs(new.maxLatitude - old.maxLatitude)
    val lonDelta = abs(new.minLongitude - old.minLongitude) + abs(new.maxLongitude - old.maxLongitude)
    return latDelta > latSpan * 0.2 || lonDelta > lonSpan * 0.2
}

/**
 * Owns RoutePlanningState and reacts to RoutePlanningEvent (CLAUDE.md #6.2 - UI renders state
 * and emits events only; this class holds the logic). Location search is debounced and
 * cancels obsolete in-flight requests via flatMapLatest (CLAUDE.md #28, #74).
 */
@OptIn(FlowPreview::class, ExperimentalCoroutinesApi::class)
@HiltViewModel
class RoutePlanningViewModel @Inject constructor(
    private val geocodingRepository: GeocodingRepository,
    private val routeRepository: RouteRepository,
    private val trafficRepository: TrafficRepository,
    connectivityObserver: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(RoutePlanningState())
    val state: StateFlow<RoutePlanningState> = _state.asStateFlow()

    // StateFlow (not SharedFlow) deliberately: it always exposes its latest value to a
    // collector even if collection starts a moment after the value was set, so an emission
    // right after ViewModel construction is never silently missed.
    private val startQueryFlow = MutableStateFlow("")
    private val destinationQueryFlow = MutableStateFlow("")
    private val trafficEnabledFlow = MutableStateFlow(false)
    private val mapBoundsFlow = MutableStateFlow<MapBounds?>(null)

    init {
        connectivityObserver.isOnline()
            .onEach { online -> _state.update { it.copy(isOffline = !online) } }
            .launchIn(viewModelScope)

        observeSearch(startQueryFlow, isStart = true)
        observeSearch(destinationQueryFlow, isStart = false)
        observeTrafficArea()
    }

    fun onEvent(event: RoutePlanningEvent) {
        when (event) {
            is RoutePlanningEvent.StartQueryChanged -> onQueryChanged(event.query, isStart = true)
            is RoutePlanningEvent.DestinationQueryChanged -> onQueryChanged(event.query, isStart = false)
            is RoutePlanningEvent.StartLocationSelected -> onLocationSelected(event.suggestion, isStart = true)
            is RoutePlanningEvent.DestinationLocationSelected ->
                onLocationSelected(event.suggestion, isStart = false)
            RoutePlanningEvent.StartFieldFocused ->
                _state.update { it.copy(activeSuggestionField = ActiveSuggestionField.START) }
            RoutePlanningEvent.DestinationFieldFocused ->
                _state.update { it.copy(activeSuggestionField = ActiveSuggestionField.DESTINATION) }
            RoutePlanningEvent.SuggestionsDismissed ->
                _state.update { it.copy(activeSuggestionField = ActiveSuggestionField.NONE) }
            RoutePlanningEvent.ClearStartLocation -> _state.update {
                it.copy(startQuery = "", startLocation = null, startSuggestions = emptyList())
            }
            RoutePlanningEvent.ClearDestinationLocation -> _state.update {
                it.copy(destinationQuery = "", destinationLocation = null, destinationSuggestions = emptyList())
            }
            RoutePlanningEvent.OptimizeRouteClicked -> planRoute()
            RoutePlanningEvent.RetryClicked -> {
                _state.update { it.copy(error = null) }
                planRoute()
            }
            RoutePlanningEvent.ErrorDismissed -> _state.update { it.copy(error = null) }
            RoutePlanningEvent.TrafficToggled -> onTrafficToggled()
            is RoutePlanningEvent.MapBoundsChanged -> mapBoundsFlow.value = event.bounds
        }
    }

    private fun onTrafficToggled() {
        val enabling = !_state.value.trafficEnabled
        _state.update {
            it.copy(
                trafficEnabled = enabling,
                trafficLayerStatus = if (enabling) TrafficLayerStatus.LOADING else TrafficLayerStatus.OFF,
                trafficSegments = if (enabling) it.trafficSegments else emptyList(),
            )
        }
        trafficEnabledFlow.value = enabling
    }

    private fun observeTrafficArea() {
        combine(trafficEnabledFlow, mapBoundsFlow) { enabled, bounds -> enabled to bounds }
            .filter { (enabled, bounds) -> enabled && bounds != null }
            .debounce(TRAFFIC_DEBOUNCE_MS)
            .distinctUntilChanged { old, new ->
                // Only significant for the (enabled, bounds) pair when both are enabled and the
                // bounds barely moved - a disable->enable transition must always pass through.
                old.first && new.first && old.second != null && new.second != null &&
                    !isSignificantBoundsChange(old.second!!, new.second!!)
            }
            .flatMapLatest { (_, bounds) -> flow { emit(trafficRepository.getTrafficArea(bounds!!)) } }
            .onEach { result ->
                if (!_state.value.trafficEnabled) return@onEach
                when (result) {
                    is QTraceResult.Success -> _state.update {
                        it.copy(
                            trafficLayerStatus = if (result.data.available) {
                                TrafficLayerStatus.LIVE
                            } else {
                                TrafficLayerStatus.UNAVAILABLE
                            },
                            trafficSegments = result.data.segments,
                            trafficSource = result.data.source,
                            trafficUpdatedAt = result.data.updatedAt,
                        )
                    }
                    // A failed traffic request never blocks route planning or shows the
                    // screen-wide error banner (CLAUDE.md traffic master-prompt #34) - the map
                    // and the rest of the screen keep working.
                    is QTraceResult.Failure -> _state.update {
                        it.copy(trafficLayerStatus = TrafficLayerStatus.UNAVAILABLE, trafficSegments = emptyList())
                    }
                }
            }
            .launchIn(viewModelScope)
    }

    private fun onQueryChanged(query: String, isStart: Boolean) {
        _state.update {
            if (isStart) {
                it.copy(startQuery = query, startLocation = null, activeSuggestionField = ActiveSuggestionField.START)
            } else {
                it.copy(
                    destinationQuery = query,
                    destinationLocation = null,
                    activeSuggestionField = ActiveSuggestionField.DESTINATION,
                )
            }
        }
        val flow = if (isStart) startQueryFlow else destinationQueryFlow
        flow.value = query
    }

    private fun onLocationSelected(suggestion: LocationSuggestion, isStart: Boolean) {
        _state.update {
            if (isStart) {
                it.copy(
                    startQuery = suggestion.label,
                    startLocation = suggestion,
                    startSuggestions = emptyList(),
                    activeSuggestionField = ActiveSuggestionField.NONE,
                )
            } else {
                it.copy(
                    destinationQuery = suggestion.label,
                    destinationLocation = suggestion,
                    destinationSuggestions = emptyList(),
                    activeSuggestionField = ActiveSuggestionField.NONE,
                )
            }
        }
    }

    private fun observeSearch(queryFlow: MutableStateFlow<String>, isStart: Boolean) {
        queryFlow
            .debounce(SEARCH_DEBOUNCE_MS)
            .distinctUntilChanged()
            .onEach { query ->
                val searching = query.trim().length >= MIN_QUERY_LENGTH
                _state.update {
                    if (isStart) it.copy(isSearchingStart = searching) else it.copy(isSearchingDestination = searching)
                }
            }
            .flatMapLatest { query ->
                if (query.trim().length < MIN_QUERY_LENGTH) {
                    flowOf(QTraceResult.Success(emptyList()))
                } else {
                    flow { emit(geocodingRepository.search(query.trim())) }
                }
            }
            .onEach { result ->
                when (result) {
                    is QTraceResult.Success -> _state.update {
                        if (isStart) {
                            it.copy(startSuggestions = result.data, isSearchingStart = false)
                        } else {
                            it.copy(destinationSuggestions = result.data, isSearchingDestination = false)
                        }
                    }
                    is QTraceResult.Failure -> _state.update {
                        val cleared = if (isStart) {
                            it.copy(startSuggestions = emptyList(), isSearchingStart = false)
                        } else {
                            it.copy(destinationSuggestions = emptyList(), isSearchingDestination = false)
                        }
                        cleared.copy(error = result.error)
                    }
                }
            }
            .launchIn(viewModelScope)
    }

    private fun planRoute() {
        val current = _state.value
        val origin = current.startLocation
        val destination = current.destinationLocation
        if (origin == null || destination == null || !current.canOptimize) return

        _state.update { it.copy(isPlanningRoute = true, error = null) }
        viewModelScope.launch {
            when (val result = routeRepository.planRoute(origin.coordinate, destination.coordinate)) {
                is QTraceResult.Success -> _state.update {
                    it.copy(isPlanningRoute = false, optimizationResult = result.data)
                }
                is QTraceResult.Failure -> _state.update {
                    it.copy(isPlanningRoute = false, error = result.error)
                }
            }
        }
    }
}
