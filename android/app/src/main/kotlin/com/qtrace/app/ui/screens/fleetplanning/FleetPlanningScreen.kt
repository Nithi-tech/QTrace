package com.qtrace.app.ui.screens.fleetplanning

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.qtrace.app.ui.components.ErrorBanner
import com.qtrace.app.ui.components.OfflineBanner

private val STEP_ORDER = FleetPlanningStep.entries.filter { it != FleetPlanningStep.RESULTS }

/**
 * Multi-vehicle VRP wizard: Scenario -> Depot -> Destinations -> Fleet -> Review (map) ->
 * Results. Destinations come before Fleet so the Fleet step can suggest a minimum vehicle count
 * for the destinations already entered. Entirely additive - the original single-vehicle
 * RoutePlanningScreen is unchanged and reachable as before.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FleetPlanningScreen(onExit: () -> Unit, viewModel: FleetPlanningViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()

    // The hardware/gesture back action should step back one wizard screen, matching the
    // in-app Back button - not silently exit the whole flow and discard everything entered
    // so far. Only the first step (and the terminal Results step) exits for real.
    BackHandler(enabled = state.step != FleetPlanningStep.SCENARIO) {
        if (state.step == FleetPlanningStep.RESULTS) onExit() else viewModel.onEvent(FleetPlanningEvent.BackStepClicked)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(titleFor(state.step)) },
                navigationIcon = {
                    IconButton(onClick = {
                        if (state.step == FleetPlanningStep.SCENARIO) onExit() else viewModel.onEvent(FleetPlanningEvent.BackStepClicked)
                    }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
    ) { paddingValues ->
        Column(modifier = Modifier.fillMaxSize().padding(paddingValues)) {
            if (state.step != FleetPlanningStep.RESULTS) {
                val progress = (STEP_ORDER.indexOf(state.step) + 1f) / STEP_ORDER.size
                LinearProgressIndicator(progress = { progress }, modifier = Modifier.fillMaxWidth())
            }

            if (state.isOffline) {
                OfflineBanner(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp))
            }
            state.error?.let { error ->
                ErrorBanner(
                    error = error,
                    onRetry = { viewModel.onEvent(FleetPlanningEvent.RetryClicked) },
                    onDismiss = { viewModel.onEvent(FleetPlanningEvent.ErrorDismissed) },
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
                )
            }

            Column(modifier = Modifier.weight(1f).fillMaxWidth()) {
                when (state.step) {
                    FleetPlanningStep.SCENARIO -> ScenarioStep(state, viewModel::onEvent)
                    FleetPlanningStep.DEPOT -> DepotStep(state, viewModel::onEvent)
                    FleetPlanningStep.DESTINATIONS -> DestinationsStep(state, viewModel::onEvent)
                    FleetPlanningStep.FLEET -> FleetStep(state, viewModel::onEvent)
                    FleetPlanningStep.REVIEW -> ReviewStep(state, viewModel::onEvent)
                    FleetPlanningStep.RESULTS -> ResultsStep(state, viewModel::onEvent)
                }
            }

            if (state.step != FleetPlanningStep.REVIEW && state.step != FleetPlanningStep.RESULTS) {
                Row(modifier = Modifier.fillMaxWidth().padding(16.dp)) {
                    Button(
                        onClick = { viewModel.onEvent(FleetPlanningEvent.NextStepClicked) },
                        enabled = canProceed(state),
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Text("Next")
                    }
                }
            }
        }
    }
}

private fun canProceed(state: FleetPlanningState): Boolean = when (state.step) {
    FleetPlanningStep.SCENARIO -> state.canProceedFromScenario
    FleetPlanningStep.DEPOT -> state.canProceedFromDepot
    FleetPlanningStep.DESTINATIONS -> state.canProceedFromDestinations
    FleetPlanningStep.FLEET -> state.canProceedFromFleet
    FleetPlanningStep.REVIEW, FleetPlanningStep.RESULTS -> true
}

private fun titleFor(step: FleetPlanningStep): String = when (step) {
    FleetPlanningStep.SCENARIO -> "Plan Fleet Routes"
    FleetPlanningStep.DEPOT -> "Depot / Starting Location"
    FleetPlanningStep.DESTINATIONS -> "Destinations"
    FleetPlanningStep.FLEET -> "Available Fleet"
    FleetPlanningStep.REVIEW -> "Review & Generate"
    FleetPlanningStep.RESULTS -> "Optimized Routes"
}
