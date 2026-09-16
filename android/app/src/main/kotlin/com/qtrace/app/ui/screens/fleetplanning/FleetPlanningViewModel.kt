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
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.FlowPreview
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

/** Owns FleetPlanningState and reacts to FleetPlanningEvent (CLAUDE.md #6.2), mirroring
 * RoutePlanningViewModel's pattern for the new multi-vehicle wizard flow. */
@OptIn(FlowPreview::class, ExperimentalCoroutinesApi::class)
@HiltViewModel
class FleetPlanningViewModel @Inject constructor(
    private val geocodingRepository: GeocodingRepository,
    private val fleetRepository: FleetRepository,
    connectivityObserver: ConnectivityObserver,
) : ViewModel() {

    private val _state = MutableStateFlow(FleetPlanningState())
    val state: StateFlow<FleetPlanningState> = _state.asStateFlow()

    private val depotQueryFlow = MutableStateFlow("")

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
            is FleetPlanningEvent.RemoveDestination -> _state.update {
                it.copy(destinations = it.destinations.filterNot { d -> d.id == event.id })
            }
            is FleetPlanningEvent.DestinationFieldChanged -> _state.update {
                it.copy(
                    destinations = it.destinations.map { d ->
                        if (d.id == event.id) updateDestinationField(d, event.field, event.value) else d
                    },
                )
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
            FleetPlanningEvent.StartOverClicked -> _state.update { FleetPlanningState() }
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
            DestinationField.NAME -> destination.copy(name = value, address = value)
            DestinationField.DEMAND -> destination.copy(demand = value)
            DestinationField.TIME_WINDOW_START -> destination.copy(timeWindowStart = value)
            DestinationField.TIME_WINDOW_END -> destination.copy(timeWindowEnd = value)
            DestinationField.SERVICE_TIME_MINUTES -> destination.copy(serviceTimeMinutes = value)
            DestinationField.LATITUDE -> destination.copy(latitude = value)
            DestinationField.LONGITUDE -> destination.copy(longitude = value)
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
            FleetPlanningStep.DEPOT -> FleetPlanningStep.FLEET
            FleetPlanningStep.FLEET -> FleetPlanningStep.DESTINATIONS
            FleetPlanningStep.DESTINATIONS -> FleetPlanningStep.REVIEW
            FleetPlanningStep.REVIEW -> FleetPlanningStep.REVIEW
            FleetPlanningStep.RESULTS -> FleetPlanningStep.RESULTS
        }
        _state.update { it.copy(step = next) }
    }

    private fun retreatStep() {
        val previous = when (_state.value.step) {
            FleetPlanningStep.SCENARIO -> FleetPlanningStep.SCENARIO
            FleetPlanningStep.DEPOT -> FleetPlanningStep.SCENARIO
            FleetPlanningStep.FLEET -> FleetPlanningStep.DEPOT
            FleetPlanningStep.DESTINATIONS -> FleetPlanningStep.FLEET
            FleetPlanningStep.REVIEW -> FleetPlanningStep.DESTINATIONS
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
                is QTraceResult.Success -> _state.update {
                    it.copy(isSubmitting = false, result = result.data, step = FleetPlanningStep.RESULTS)
                }
                is QTraceResult.Failure -> _state.update { it.copy(isSubmitting = false, error = result.error) }
            }
        }
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
        address = if (effectiveCoordinate == null) (address ?: name) else null,
        coordinate = effectiveCoordinate,
        demand = demand.toDoubleOrNull() ?: 0.0,
        timeWindowStart = timeWindowStart.ifBlank { null },
        timeWindowEnd = timeWindowEnd.ifBlank { null },
        serviceTimeSeconds = (serviceTimeMinutes.toIntOrNull() ?: 0) * 60,
    )
