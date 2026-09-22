package com.qtrace.app.ui.screens.fleetplanning

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.qtrace.app.data.network.ConnectivityObserver
import com.qtrace.app.domain.model.FleetDestination
import com.qtrace.app.domain.model.FleetRouteRequest
import com.qtrace.app.domain.model.QTraceResult
import com.qtrace.app.domain.model.VehicleSpec
import com.qtrace.app.domain.repository.FleetRepository
import com.qtrace.app.domain.repository.GeocodingRepository
import com.qtrace.app.domain.repository.TrackingRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.debounce
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.launchIn
import kotlinx.coroutines.flow.onEach
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

private const val SEARCH_DEBOUNCE_MS = 350L
private const val MIN_QUERY_LENGTH = 2
private const val LIVE_TRACKING_POLL_INTERVAL_MS = 8_000L

/** Owns FleetPlanningState and reacts to FleetPlanningEvent (CLAUDE.md #6.2), mirroring
 * RoutePlanningViewModel's pattern for the new multi-vehicle wizard flow. */
@OptIn(FlowPreview::class, ExperimentalCoroutinesApi::class)
@HiltViewModel
class FleetPlanningViewModel @Inject constructor(
    private val geocodingRepository: GeocodingRepository,
    private val fleetRepository: FleetRepository,
    private val trackingRepository: TrackingRepository,
    connectivityObserver: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(FleetPlanningState())
    val state: StateFlow<FleetPlanningState> = _state.asStateFlow()

    private val depotQueryFlow = MutableStateFlow("")
    private var liveTrackingJob: Job? = null

    // Destinations are a dynamic list (rows added/removed at runtime), so each row's debounced
    // search is a cancellable coroutine Job keyed by that row's id, rather than a fixed
    // MutableStateFlow per field like depotQueryFlow - this scales to any number of rows and
    // cleans up naturally when a row is removed.
    private val destinationSearchJobs = mutableMapOf<String, Job>()

    init {
        connectivityObserver.isOnline()
            .onEach { online -> _state.update { it.copy(isOffline = !online) } }
            .launchIn(viewModelScope)

        depotQueryFlow
            .debounce(SEARCH_DEBOUNCE_MS)
            .distinctUntilChanged()
            .onEach { query -> _state.update { it.copy(isSearchingDepot = query.trim().length >= MIN_QUERY_LENGTH) } }
            .flatMapLatest { query ->
                if (query.trim().length < MIN_QUERY_LENGTH) {
                    flowOf(QTraceResult.Success(emptyList()))
                } else {
                    flow { emit(geocodingRepository.search(query.trim())) }
                }
            }
            .onEach { result ->
                when (result) {
                    is QTraceResult.Success ->
                        _state.update { it.copy(depotSuggestions = result.data, isSearchingDepot = false) }
                    is QTraceResult.Failure ->
                        _state.update { it.copy(depotSuggestions = emptyList(), isSearchingDepot = false, error = result.error) }
                }
            }
            .launchIn(viewModelScope)
    }

    fun onEvent(event: FleetPlanningEvent) {
        when (event) {
            is FleetPlanningEvent.ScenarioSelected -> _state.update { it.copy(scenario = event.scenario) }

            is FleetPlanningEvent.DepotQueryChanged -> {
                _state.update { it.copy(depotQuery = event.query, depot = null) }
                depotQueryFlow.value = event.query
            }
            FleetPlanningEvent.DepotFieldFocused -> Unit
            FleetPlanningEvent.DepotSuggestionsDismissed -> _state.update { it.copy(depotSuggestions = emptyList()) }
            is FleetPlanningEvent.DepotSelected -> _state.update {
                it.copy(depotQuery = event.suggestion.label, depot = event.suggestion, depotSuggestions = emptyList())
            }
            FleetPlanningEvent.ClearDepot -> _state.update {
                it.copy(depotQuery = "", depot = null, depotSuggestions = emptyList())
            }
            is FleetPlanningEvent.ReturnToDepotToggled -> _state.update { it.copy(returnToDepot = event.value) }

            FleetPlanningEvent.AddVehicle -> _state.update { it.copy(vehicles = it.vehicles + VehicleSpecInput()) }
            is FleetPlanningEvent.RemoveVehicle -> _state.update {
                it.copy(vehicles = it.vehicles.filterNot { v -> v.id == event.id })
            }
            is FleetPlanningEvent.VehicleFieldChanged -> _state.update {
                it.copy(vehicles = it.vehicles.map { v -> if (v.id == event.id) updateVehicleField(v, event.field, event.value) else v })
            }

            FleetPlanningEvent.AddDestination -> _state.update { it.copy(destinations = it.destinations + DestinationInput()) }
            is FleetPlanningEvent.RemoveDestination -> {
                destinationSearchJobs.remove(event.id)?.cancel()
                _state.update { it.copy(destinations = it.destinations.filterNot { d -> d.id == event.id }) }
            }
            is FleetPlanningEvent.DestinationFieldChanged -> _state.update {
                it.copy(
                    destinations = it.destinations.map { d ->
                        if (d.id == event.id) updateDestinationField(d, event.field, event.value) else d
                    },
                )
            }
            is FleetPlanningEvent.DestinationQueryChanged -> onDestinationQueryChanged(event.id, event.query)
            is FleetPlanningEvent.DestinationFieldFocused -> Unit
            is FleetPlanningEvent.DestinationSuggestionsDismissed -> updateDestination(event.id) { it.copy(suggestions = emptyList()) }
            is FleetPlanningEvent.DestinationSuggestionSelected -> {
                destinationSearchJobs.remove(event.id)?.cancel()
                updateDestination(event.id) {
                    it.copy(
                        query = event.suggestion.label,
                        name = event.suggestion.label,
                        coordinate = event.suggestion.coordinate,
                        address = null,
                        suggestions = emptyList(),
                        isSearching = false,
                    )
                }
            }
            is FleetPlanningEvent.ClearDestinationLocation -> {
                destinationSearchJobs.remove(event.id)?.cancel()
                updateDestination(event.id) {
                    it.copy(query = "", name = "", address = null, coordinate = null, suggestions = emptyList(), isSearching = false)
                }
            }
            is FleetPlanningEvent.ManualCoordinateEntered -> updateDestination(event.id) { destination ->
                val label = "(${event.coordinate.latitude}, ${event.coordinate.longitude})"
                destination.copy(query = label, name = label, coordinate = event.coordinate, address = null)
            }
            is FleetPlanningEvent.CsvImported -> importCsv(event.csvContent)
            FleetPlanningEvent.CsvImportErrorDismissed -> _state.update { it.copy(csvImportError = null) }

            is FleetPlanningEvent.ObjectiveSelected -> _state.update { it.copy(objective = event.objective) }

            FleetPlanningEvent.NextStepClicked -> advanceStep()
            FleetPlanningEvent.BackStepClicked -> retreatStep()
            FleetPlanningEvent.GenerateRoutesClicked -> generateRoutes()
            FleetPlanningEvent.RetryClicked -> {
                _state.update { it.copy(error = null) }
                generateRoutes()
            }
            FleetPlanningEvent.ErrorDismissed -> _state.update { it.copy(error = null) }
            FleetPlanningEvent.StartOverClicked -> {
                liveTrackingJob?.cancel()
                _state.update { FleetPlanningState() }
            }
        }
    }

    private fun updateVehicleField(vehicle: VehicleSpecInput, field: VehicleField, value: String): VehicleSpecInput =
        when (field) {
            VehicleField.TYPE -> vehicle.copy(vehicleType = value)
            VehicleField.COUNT -> vehicle.copy(count = value)
            VehicleField.CAPACITY -> vehicle.copy(capacity = value)
            VehicleField.COST_PER_KM -> vehicle.copy(costPerKm = value)
            VehicleField.AVAILABILITY_START -> vehicle.copy(availabilityStart = value)
            VehicleField.AVAILABILITY_END -> vehicle.copy(availabilityEnd = value)
        }

    private fun updateDestinationField(destination: DestinationInput, field: DestinationField, value: String): DestinationInput =
        when (field) {
            DestinationField.DEMAND -> destination.copy(demand = value)
            DestinationField.TIME_WINDOW_START -> destination.copy(timeWindowStart = value)
            DestinationField.TIME_WINDOW_END -> destination.copy(timeWindowEnd = value)
            DestinationField.SERVICE_TIME_MINUTES -> destination.copy(serviceTimeMinutes = value)
        }

    private fun updateDestination(id: String, transform: (DestinationInput) -> DestinationInput) {
        _state.update { state -> state.copy(destinations = state.destinations.map { if (it.id == id) transform(it) else it }) }
    }

    /** Mirrors the depot search debounce, but per-row via a cancellable Job instead of a Flow,
     * since destinations are a dynamic list rather than one fixed field (see
     * [destinationSearchJobs]). This is the fix for destinations being resolved unreliably from
     * a bare typed name: the user now sees and picks a real geocoded suggestion, exactly like
     * the depot field, instead of the name being sent to the backend on faith. */
    private fun onDestinationQueryChanged(id: String, query: String) {
        updateDestination(id) { it.copy(query = query, name = "", coordinate = null, address = null, suggestions = emptyList()) }
        destinationSearchJobs[id]?.cancel()

        val trimmed = query.trim()
        if (trimmed.length < MIN_QUERY_LENGTH) {
            updateDestination(id) { it.copy(isSearching = false) }
            return
        }

        destinationSearchJobs[id] = viewModelScope.launch {
            updateDestination(id) { it.copy(isSearching = true) }
            try {
                delay(SEARCH_DEBOUNCE_MS)
                when (val result = geocodingRepository.search(trimmed)) {
                    is QTraceResult.Success -> updateDestination(id) { it.copy(suggestions = result.data, isSearching = false) }
                    is QTraceResult.Failure -> {
                        updateDestination(id) { it.copy(suggestions = emptyList(), isSearching = false) }
                        _state.update { it.copy(error = result.error) }
                    }
                }
            } catch (cancellation: CancellationException) {
                throw cancellation
            }
        }
    }

    private fun importCsv(csvContent: String) {
        try {
            val imported = CsvDestinationParser.parse(csvContent)
            _state.update { it.copy(destinations = it.destinations + imported, csvImportError = null) }
        } catch (parseError: CsvParseException) {
            _state.update { it.copy(csvImportError = parseError.message) }
        }
    }

    private fun advanceStep() {
        val current = _state.value
        val canAdvance = when (current.step) {
            FleetPlanningStep.SCENARIO -> current.canProceedFromScenario
            FleetPlanningStep.DEPOT -> current.canProceedFromDepot
            FleetPlanningStep.FLEET -> current.canProceedFromFleet
            FleetPlanningStep.DESTINATIONS -> current.canProceedFromDestinations
            FleetPlanningStep.REVIEW -> true
            FleetPlanningStep.RESULTS -> false
        }
        if (!canAdvance) return

        val next = when (current.step) {
            FleetPlanningStep.SCENARIO -> FleetPlanningStep.DEPOT
            FleetPlanningStep.DEPOT -> FleetPlanningStep.DESTINATIONS
            FleetPlanningStep.DESTINATIONS -> FleetPlanningStep.FLEET
            FleetPlanningStep.FLEET -> FleetPlanningStep.REVIEW
            FleetPlanningStep.REVIEW -> FleetPlanningStep.REVIEW
            FleetPlanningStep.RESULTS -> FleetPlanningStep.RESULTS
        }
        _state.update { it.copy(step = next) }
    }

    private fun retreatStep() {
        val previous = when (_state.value.step) {
            FleetPlanningStep.SCENARIO -> FleetPlanningStep.SCENARIO
            FleetPlanningStep.DEPOT -> FleetPlanningStep.SCENARIO
            FleetPlanningStep.DESTINATIONS -> FleetPlanningStep.DEPOT
            FleetPlanningStep.FLEET -> FleetPlanningStep.DESTINATIONS
            FleetPlanningStep.REVIEW -> FleetPlanningStep.FLEET
            FleetPlanningStep.RESULTS -> FleetPlanningStep.REVIEW
        }
        _state.update { it.copy(step = previous) }
    }

    private fun generateRoutes() {
        val current = _state.value
        val depot = current.depot ?: return
        if (!current.canGenerateRoutes) return

        _state.update { it.copy(isSubmitting = true, error = null) }
        viewModelScope.launch {
            val request = FleetRouteRequest(
                scenario = current.scenario ?: return@launch,
                depot = depot.coordinate,
                returnToDepot = current.returnToDepot,
                vehicles = current.vehicles.map { it.toDomain() },
                destinations = current.destinations.map { it.toDomain() },
                objective = current.objective,
            )
            when (val result = fleetRepository.planFleetRoutes(request)) {
                is QTraceResult.Success -> {
                    _state.update {
                        it.copy(isSubmitting = false, result = result.data, step = FleetPlanningStep.RESULTS)
                    }
                    startLiveTracking(result.data.planningSessionId)
                }
                is QTraceResult.Failure -> _state.update { it.copy(isSubmitting = false, error = result.error) }
            }
        }
    }

    /** Whoever just generated this fleet's routes already IS the admin for it - there is no
     * separate admin login or session-id entry. As soon as routes exist, this starts polling
     * that same planning run's live status so ResultsStep can show current vehicle locations,
     * distance travelled, and off-route warnings without the user doing anything else. */
    private fun startLiveTracking(sessionId: String?) {
        if (sessionId == null) return
        liveTrackingJob?.cancel()
        liveTrackingJob = viewModelScope.launch {
            while (true) {
                when (val result = trackingRepository.getFleetOverview(sessionId)) {
                    is QTraceResult.Success -> _state.update { it.copy(liveTracking = result.data) }
                    is QTraceResult.Failure -> Unit // transient - keep the last-known-good overview and retry
                }
                delay(LIVE_TRACKING_POLL_INTERVAL_MS)
            }
        }
    }

    override fun onCleared() {
        liveTrackingJob?.cancel()
        super.onCleared()
    }
}

private fun VehicleSpecInput.toDomain(): VehicleSpec =
    VehicleSpec(
        vehicleType = vehicleType,
        count = count.toIntOrNull() ?: 1,
        capacity = capacity.toDoubleOrNull() ?: 0.0,
        costPerKm = costPerKm.toDoubleOrNull() ?: 0.0,
        availabilityStart = availabilityStart.ifBlank { null },
        availabilityEnd = availabilityEnd.ifBlank { null },
    )

private fun DestinationInput.toDomain(): FleetDestination =
    FleetDestination(
        name = name,
        address = if (coordinate == null) (address ?: name) else null,
        coordinate = coordinate,
        demand = demand.toDoubleOrNull() ?: 0.0,
        timeWindowStart = timeWindowStart.ifBlank { null },
        timeWindowEnd = timeWindowEnd.ifBlank { null },
        serviceTimeSeconds = (serviceTimeMinutes.toIntOrNull() ?: 0) * 60,
    )
