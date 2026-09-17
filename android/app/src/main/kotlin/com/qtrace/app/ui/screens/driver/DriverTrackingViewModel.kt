package com.qtrace.app.ui.screens.driver

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.qtrace.app.domain.model.Coordinate
import com.qtrace.app.domain.model.QTraceResult
import com.qtrace.app.domain.repository.TrackingRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.util.Locale
import javax.inject.Inject
import kotlin.math.asin
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin
import kotlin.math.sqrt

private const val EARTH_RADIUS_METERS = 6_371_000.0

private fun haversineMeters(a: Coordinate, b: Coordinate): Double {
    val lat1 = Math.toRadians(a.latitude)
    val lat2 = Math.toRadians(b.latitude)
    val dLat = Math.toRadians(b.latitude - a.latitude)
    val dLon = Math.toRadians(b.longitude - a.longitude)
    val h = sin(dLat / 2).let { it * it } + cos(lat1) * cos(lat2) * sin(dLon / 2).let { it * it }
    return 2 * EARTH_RADIUS_METERS * asin(sqrt(min(1.0, h)))
}

/** Owns DriverTrackingState and reacts to DriverTrackingEvent, mirroring the rest of this app's
 * screens (CLAUDE.md #6.2). GPS updates arrive from the screen's LocationManager listener as
 * [DriverTrackingEvent.LocationUpdated] and are both shown locally (running distance) and sent
 * to the backend as a ping - the backend is the source of truth for anyone else watching (the
 * admin view), this view model's own running total is just for the driver's immediate feedback. */
@HiltViewModel
class DriverTrackingViewModel @Inject constructor(
    private val trackingRepository: TrackingRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(DriverTrackingState())
    val state: StateFlow<DriverTrackingState> = _state.asStateFlow()

    fun onEvent(event: DriverTrackingEvent) {
        when (event) {
            is DriverTrackingEvent.CodeInputChanged ->
                _state.update { it.copy(codeInput = event.value.uppercase(Locale.ROOT), error = null) }
            DriverTrackingEvent.StartTrackingClicked -> startTracking()
            DriverTrackingEvent.RetryClicked -> startTracking()
            DriverTrackingEvent.ErrorDismissed -> _state.update { it.copy(error = null) }
            DriverTrackingEvent.StopTrackingClicked -> _state.update { DriverTrackingState() }
            is DriverTrackingEvent.LocationPermissionResult ->
                _state.update { it.copy(locationPermissionGranted = event.granted) }
            is DriverTrackingEvent.LocationUpdated -> onLocationUpdated(event.coordinate)
        }
    }

    private fun startTracking() {
        val code = _state.value.codeInput.trim()
        if (code.isBlank()) return

        viewModelScope.launch {
            _state.update { it.copy(isLoading = true, error = null) }
            when (val result = trackingRepository.getAssignedRoute(code)) {
                is QTraceResult.Success -> _state.update {
                    it.copy(isLoading = false, step = DriverTrackingStep.TRACKING, assignedRoute = result.data)
                }
                is QTraceResult.Failure -> _state.update { it.copy(isLoading = false, error = result.error) }
            }
        }
    }

    private fun onLocationUpdated(coordinate: Coordinate) {
        val previous = _state.value.currentLocation
        val addedDistance = previous?.let { haversineMeters(it, coordinate) } ?: 0.0
        _state.update {
            it.copy(
                currentLocation = coordinate,
                distanceTravelledMeters = it.distanceTravelledMeters + addedDistance,
            )
        }

        val code = _state.value.assignedRoute?.trackingCode ?: return
        viewModelScope.launch {
            when (trackingRepository.postLocationPing(code, coordinate)) {
                is QTraceResult.Success -> _state.update { it.copy(lastPingFailed = false) }
                is QTraceResult.Failure -> _state.update { it.copy(lastPingFailed = true) }
            }
        }
    }
}
