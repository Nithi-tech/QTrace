package com.qtrace.app.ui.screens.fleetplanning

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.qtrace.app.BuildConfig
import com.qtrace.app.domain.model.OptimizationObjective
import com.qtrace.app.ui.components.MapLibreFleetMap

/** Spec section 12 map-preview step, plus optimization objective (spec section 6), before
 * calling the backend (spec sections 7-10 happen server-side in FleetOptimizationService). */
@Composable
fun ReviewStep(state: FleetPlanningState, onEvent: (FleetPlanningEvent) -> Unit) {
    Column(modifier = Modifier.fillMaxSize()) {
        Column(modifier = Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(text = "Optimize for", style = MaterialTheme.typography.titleMedium)
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(OptimizationObjective.entries) { objective ->
                    FilterChip(
                        selected = state.objective == objective,
                        onClick = { onEvent(FleetPlanningEvent.ObjectiveSelected(objective)) },
                        label = { Text(objective.displayName) },
                    )
                }
            }
            Text(
                text = "${state.vehicles.sumOf { it.count.toIntOrNull() ?: 0 }} vehicle(s), " +
                    "${state.destinations.size} destination(s)",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }

        Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
            MapLibreFleetMap(
                styleUrl = BuildConfig.MAP_STYLE_URL,
                depot = state.depot?.coordinate,
                destinations = state.destinations.mapNotNull { it.effectiveCoordinate },
                vehicleRoutes = emptyList(),
                modifier = Modifier.fillMaxSize(),
            )

            if (state.isSubmitting) {
                Surface(
                    modifier = Modifier.align(Alignment.Center).padding(16.dp),
                    shape = MaterialTheme.shapes.medium,
                    tonalElevation = 4.dp,
                ) {
                    Row {
                        CircularProgressIndicator(modifier = Modifier.padding(16.dp))
                        Text(
                            text = "Optimizing routes...",
                            modifier = Modifier.align(Alignment.CenterVertically).padding(end = 16.dp),
                        )
                    }
                }
            }
        }

        Row(modifier = Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = { onEvent(FleetPlanningEvent.BackStepClicked) }, modifier = Modifier.weight(1f)) {
                Text("Back")
            }
            Button(
                onClick = { onEvent(FleetPlanningEvent.GenerateRoutesClicked) },
                enabled = state.canGenerateRoutes,
                modifier = Modifier.weight(1f),
            ) {
                Text("Generate Optimized Routes")
            }
        }
    }
}
