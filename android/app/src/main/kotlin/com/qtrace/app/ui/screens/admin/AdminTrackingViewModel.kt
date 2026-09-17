package com.qtrace.app.ui.screens.admin

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.qtrace.app.domain.model.QTraceResult
import com.qtrace.app.domain.repository.TrackingRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

private const val POLL_INTERVAL_MS = 8_000L

/** Owns AdminTrackingState and reacts to AdminTrackingEvent (CLAUDE.md #6.2). Once a job id is
 * loaded, this polls the fleet overview on an interval so the admin's map/list stay live without
 * the admin having to refresh - a WebSocket would push updates instead, but this app has no
 * real-time infra anywhere else either, so plain polling matches the rest of the codebase
 * (CLAUDE.md #15/#25 - don't add infrastructure before it's needed). */
@HiltViewModel
class AdminTrackingViewModel @Inject constructor(
    private val trackingRepository: TrackingRepository,
) : ViewModel() {

    private val _state = MutableStateFlow(AdminTrackingState())
    val state: StateFlow<AdminTrackingState> = _state.asStateFlow()

    private var pollingJob: Job? = null

    fun onEvent(event: AdminTrackingEvent) {
        when (event) {
            is AdminTrackingEvent.JobIdInputChanged -> _state.update { it.copy(jobIdInput = event.value, error = null) }
            AdminTrackingEvent.LoadClicked -> load()
            AdminTrackingEvent.RetryClicked -> load()
            AdminTrackingEvent.ErrorDismissed -> _state.update { it.copy(error = null) }
            AdminTrackingEvent.StopViewingClicked -> {
                pollingJob?.cancel()
                _state.update { AdminTrackingState() }
            }
        }
    }

    private fun load() {
        val jobId = _state.value.jobIdInput.trim()
        if (jobId.isBlank()) return

        pollingJob?.cancel()
        _state.update { it.copy(isLoading = true, error = null) }

        viewModelScope.launch {
            fetchOnce(jobId)
            pollingJob = launch {
                while (true) {
                    delay(POLL_INTERVAL_MS)
                    fetchOnce(jobId)
                }
            }
        }
    }

    private suspend fun fetchOnce(jobId: String) {
        when (val result = trackingRepository.getFleetOverview(jobId)) {
            is QTraceResult.Success ->
                _state.update { it.copy(isLoading = false, overview = result.data, isPolling = true, error = null) }
            is QTraceResult.Failure ->
                _state.update { it.copy(isLoading = false, isPolling = false, error = result.error) }
        }
    }

    override fun onCleared() {
        pollingJob?.cancel()
        super.onCleared()
    }
}
