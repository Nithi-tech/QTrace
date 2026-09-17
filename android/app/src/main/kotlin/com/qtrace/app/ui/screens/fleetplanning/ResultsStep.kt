package com.qtrace.app.ui.screens.fleetplanning

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.qtrace.app.BuildConfig
import com.qtrace.app.domain.model.FleetRouteResult
import com.qtrace.app.domain.model.VehicleRouteResult
import com.qtrace.app.ui.components.FleetRouteLegend
import com.qtrace.app.ui.components.MapLibreFleetMap
import com.qtrace.app.ui.components.colorForVehicle
import java.util.Locale
import kotlin.math.roundToInt

/** Spec section 10: vehicle-wise routes, distances/costs/utilization/violations, and a
 * multi-color map with a legend - one route per vehicle, not one route with extra labels. */
@Composable
fun ResultsStep(state: FleetPlanningState, onEvent: (FleetPlanningEvent) -> Unit) {
    val result = state.result

    Column(modifier = Modifier.fillMaxSize()) {
        if (result == null) {
            Text(
                text = "No result yet.",
                modifier = Modifier.padding(16.dp),
                style = MaterialTheme.typography.bodyMedium,
            )
            return@Column
        }

        if (!result.isFeasible) {
            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
                modifier = Modifier.fillMaxWidth().padding(16.dp),
            ) {
                Text(
                    text = result.infeasibilityReason ?: "Some destinations could not be assigned to any vehicle.",
                    modifier = Modifier.padding(12.dp),
                    color = MaterialTheme.colorScheme.onErrorContainer,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }

        Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
            MapLibreFleetMap(
                styleUrl = BuildConfig.MAP_STYLE_URL,
                depot = state.depot?.coordinate,
                destinations = state.destinations.mapNotNull { it.coordinate },
                vehicleRoutes = result.vehicleRoutes,
                modifier = Modifier.fillMaxSize(),
            )
        }

        FleetRouteLegend(vehicleRoutes = result.vehicleRoutes, modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp))

        SummaryRow(result = result, modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp))

        LazyColumn(
            modifier = Modifier.weight(1f).fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            itemsIndexed(result.vehicleRoutes) { index, route -> VehicleRouteCard(index = index, route = route) }
        }

        Button(
            onClick = { onEvent(FleetPlanningEvent.StartOverClicked) },
            modifier = Modifier.fillMaxWidth().padding(16.dp),
        ) {
            Text("Plan Another Fleet")
        }
    }
}

@Composable
private fun SummaryRow(result: FleetRouteResult, modifier: Modifier = Modifier) {
    Row(modifier = modifier.padding(vertical = 8.dp), horizontalArrangement = Arrangement.spacedBy(24.dp)) {
        Metric("Vehicles used", result.vehicleRoutes.size.toString())
        Metric("Total distance", formatDistance(result.totalDistanceMeters))
        Metric("Total time", formatDuration(result.totalDurationSeconds))
        Metric("Est. cost", String.format(Locale.getDefault(), "%.2f", result.totalEstimatedCost))
    }
}

@Composable
private fun Metric(label: String, value: String) {
    Column {
        Text(text = label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(text = value, style = MaterialTheme.typography.titleSmall)
    }
}

@Composable
private fun VehicleRouteCard(index: Int, route: VehicleRouteResult) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(
                    modifier = Modifier.size(12.dp),
                    shape = CircleShape,
                    color = Color(android.graphics.Color.parseColor(colorForVehicle(index))),
                ) {}
                Text(
                    text = "Vehicle ${index + 1} — ${route.vehicleType}",
                    style = MaterialTheme.typography.titleMedium,
                    modifier = Modifier.padding(start = 8.dp),
                )
            }
            Text(text = route.stopNames.joinToString(" → "), style = MaterialTheme.typography.bodyMedium)

            Row(horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                Metric("Distance", formatDistance(route.distanceMeters))
                Metric("Time", formatDuration(route.durationSeconds))
                Metric("Cost", String.format(Locale.getDefault(), "%.2f", route.estimatedCost))
            }
            Row(horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                Metric("Load", "${route.load.roundToInt()} / ${route.capacity.roundToInt()}")
                Metric("Utilization", "${(route.capacityUtilization * 100).roundToInt()}%")
            }

            if (route.timeWindowViolations.isNotEmpty()) {
                Text(
                    text = "Time window issues: ${route.timeWindowViolations.joinToString("; ")}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error,
                )
            }
        }
    }
}

private fun formatDistance(meters: Double): String =
    if (meters >= 1000) String.format(Locale.getDefault(), "%.1f km", meters / 1000.0) else "${meters.roundToInt()} m"

private fun formatDuration(seconds: Double): String {
    val totalMinutes = (seconds / 60.0).roundToInt()
    val hours = totalMinutes / 60
    val minutes = totalMinutes % 60
    return if (hours > 0) "${hours} h ${minutes} min" else "$minutes min"
}
