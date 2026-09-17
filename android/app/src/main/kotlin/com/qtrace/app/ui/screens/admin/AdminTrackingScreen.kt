package com.qtrace.app.ui.screens.admin

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.LocalShipping
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.qtrace.app.BuildConfig
import com.qtrace.app.domain.model.FleetTrackingOverview
import com.qtrace.app.domain.model.VehicleRouteResult
import com.qtrace.app.domain.model.VehicleTrackingStatus
import com.qtrace.app.ui.components.ErrorBanner
import com.qtrace.app.ui.components.FleetStopMarker
import com.qtrace.app.ui.components.MapLibreFleetMap
import com.qtrace.app.ui.components.colorForVehicle
import java.util.Locale
import kotlin.math.roundToInt

/** An administrator enters a planning_session_id to see every vehicle from that run on one live
 * map - current location, distance travelled, and an off-route warning for any vehicle that has
 * strayed from its planned route. Polls in the background (see AdminTrackingViewModel) so it
 * stays current without a manual refresh. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AdminTrackingScreen(onExit: () -> Unit, viewModel: AdminTrackingViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Admin — Fleet Tracking") },
                navigationIcon = {
                    IconButton(onClick = {
                        if (state.overview != null) {
                            viewModel.onEvent(AdminTrackingEvent.StopViewingClicked)
                        } else {
                            onExit()
                        }
                    }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
    ) { paddingValues ->
        Column(modifier = Modifier.fillMaxSize().padding(paddingValues)) {
            state.error?.let { error ->
                ErrorBanner(
                    error = error,
                    onRetry = { viewModel.onEvent(AdminTrackingEvent.RetryClicked) },
                    onDismiss = { viewModel.onEvent(AdminTrackingEvent.ErrorDismissed) },
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
                )
            }

            val overview = state.overview
            if (overview == null) {
                JobIdEntryContent(state, viewModel::onEvent)
            } else {
                FleetOverviewContent(overview)
            }
        }
    }
}

@Composable
private fun JobIdEntryContent(state: AdminTrackingState, onEvent: (AdminTrackingEvent) -> Unit) {
    Column(modifier = Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(text = "View a fleet's live tracking", style = MaterialTheme.typography.titleMedium)
        Text(
            text = "Enter the session id shown after generating routes for a fleet.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        OutlinedTextField(
            value = state.jobIdInput,
            onValueChange = { onEvent(AdminTrackingEvent.JobIdInputChanged(it)) },
            label = { Text("Session id") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Button(
            onClick = { onEvent(AdminTrackingEvent.LoadClicked) },
            enabled = state.canLoad,
            modifier = Modifier.fillMaxWidth(),
        ) {
            if (state.isLoading) {
                CircularProgressIndicator(modifier = Modifier.padding(end = 8.dp))
            }
            Text("View Fleet")
        }
    }
}

@Composable
private fun FleetOverviewContent(overview: FleetTrackingOverview) {
    val fakeRoutes = overview.vehicles.mapIndexed { index, status ->
        VehicleRouteResult(
            vehicleIndex = index,
            vehicleType = status.vehicleType,
            stopNames = status.stopNames,
            destinationIndices = emptyList(),
            distanceMeters = status.plannedDistanceMeters,
            durationSeconds = 0.0,
            load = 0.0,
            capacity = 0.0,
            capacityUtilization = 0.0,
            estimatedCost = 0.0,
            timeWindowViolations = emptyList(),
            geometry = status.geometry,
        )
    }
    val liveMarkers = overview.vehicles.mapIndexedNotNull { index, status ->
        status.currentLocation?.let { location ->
            FleetStopMarker(coordinate = location, vehicleIndex = index, isUnassigned = status.isOffRoute)
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        Box(modifier = Modifier.weight(1.1f).fillMaxWidth()) {
            MapLibreFleetMap(
                styleUrl = BuildConfig.MAP_STYLE_URL,
                depot = null,
                destinationMarkers = liveMarkers,
                vehicleRoutes = fakeRoutes,
                modifier = Modifier.fillMaxSize(),
            )
        }

        LazyColumn(
            modifier = Modifier.weight(1f).fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            itemsIndexed(overview.vehicles) { index, status -> VehicleStatusCard(index = index, status = status) }
        }
    }
}

@Composable
private fun VehicleStatusCard(index: Int, status: VehicleTrackingStatus) {
    val vehicleColor = Color(android.graphics.Color.parseColor(colorForVehicle(index)))

    Card(shape = RoundedCornerShape(16.dp), modifier = Modifier.fillMaxWidth()) {
        Row(modifier = Modifier.fillMaxWidth()) {
            Box(modifier = Modifier.width(6.dp).fillMaxHeight().background(vehicleColor))

            Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Box(
                        modifier = Modifier.size(30.dp).background(vehicleColor, CircleShape),
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(Icons.Filled.LocalShipping, contentDescription = null, tint = Color.White, modifier = Modifier.size(16.dp))
                    }
                    Column(modifier = Modifier.weight(1f)) {
                        Text(text = "Vehicle ${index + 1} — ${status.vehicleType}", style = MaterialTheme.typography.titleSmall)
                        Text(
                            text = "Code: ${status.trackingCode}",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    if (status.isOffRoute) {
                        Icon(Icons.Filled.Warning, contentDescription = "Off route", tint = MaterialTheme.colorScheme.error)
                    }
                }

                Row(horizontalArrangement = Arrangement.spacedBy(20.dp)) {
                    Metric("Travelled", formatDistance(status.distanceTravelledMeters))
                    Metric("Planned", formatDistance(status.plannedDistanceMeters))
                    Metric("Last update", status.lastPingAt?.let { "seen" } ?: "no location yet")
                }

                if (status.isOffRoute) {
                    Text(
                        text = "Off planned route by ~${status.offRouteDistanceMeters?.roundToInt() ?: 0} m",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.error,
                    )
                }
            }
        }
    }
}

@Composable
private fun Metric(label: String, value: String) {
    Column {
        Text(text = label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(text = value, style = MaterialTheme.typography.bodyMedium)
    }
}

private fun formatDistance(meters: Double): String =
    if (meters >= 1000) String.format(Locale.getDefault(), "%.1f km", meters / 1000.0) else "${meters.roundToInt()} m"
