package com.qtrace.app.ui.screens.fleetplanning

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
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.LocalShipping
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material.icons.filled.Route
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.qtrace.app.BuildConfig
import com.qtrace.app.domain.model.VehicleRouteResult
import com.qtrace.app.domain.model.VehicleTrackingStatus
import com.qtrace.app.ui.components.FleetRouteLegend
import com.qtrace.app.ui.components.FleetStopMarker
import com.qtrace.app.ui.components.MapLibreFleetMap
import com.qtrace.app.ui.components.colorForVehicle
import java.util.Locale
import kotlin.math.roundToInt

/** Vehicle-wise routes, distances/costs/utilization/violations, and a multi-color map with a
 * legend - one route per vehicle, not one route with extra labels. Each vehicle's card carries a
 * colored accent bar matching its map route/legend color, and its stops render as a numbered
 * timeline, so a route's shape and order are readable at a glance without cross-referencing the
 * map. */
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
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
                modifier = Modifier.fillMaxWidth().padding(16.dp),
            ) {
                Row(
                    modifier = Modifier.padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    Icon(Icons.Filled.Warning, contentDescription = null, tint = MaterialTheme.colorScheme.onErrorContainer)
                    Text(
                        text = result.infeasibilityReason ?: "Some destinations could not be assigned to any vehicle.",
                        color = MaterialTheme.colorScheme.onErrorContainer,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            }
        }

        val liveByVehicleIndex = state.liveTracking?.vehicles?.associateBy { it.vehicleIndex }.orEmpty()

        Box(modifier = Modifier.weight(1.2f).fillMaxWidth()) {
            MapLibreFleetMap(
                styleUrl = BuildConfig.MAP_STYLE_URL,
                depot = state.depot?.coordinate,
                destinationMarkers = state.destinations.mapIndexedNotNull { index, destination ->
                    val coordinate = destination.coordinate ?: return@mapIndexedNotNull null
                    val vehicleIndex = result.vehicleRoutes.indexOfFirst { index in it.destinationIndices }
                    val visitOrder = if (vehicleIndex >= 0) {
                        result.vehicleRoutes[vehicleIndex].destinationIndices.indexOf(index) + 1
                    } else {
                        null
                    }
                    FleetStopMarker(
                        coordinate = coordinate,
                        vehicleIndex = vehicleIndex.takeIf { it >= 0 },
                        visitOrder = visitOrder,
                        isUnassigned = index in result.unassignedDestinationIndices,
                    )
                } + result.vehicleRoutes.mapIndexedNotNull { index, route ->
                    // Each vehicle's live position (once its driver starts reporting one),
                    // colored to match its own route - this is the "admin" view: it's just the
                    // same map this fleet was planned on, now also showing where things are.
                    val location = liveByVehicleIndex[route.vehicleIndex]?.currentLocation ?: return@mapIndexedNotNull null
                    FleetStopMarker(
                        coordinate = location,
                        vehicleIndex = index,
                        isUnassigned = liveByVehicleIndex[route.vehicleIndex]?.isOffRoute == true,
                    )
                },
                vehicleRoutes = result.vehicleRoutes,
                modifier = Modifier.fillMaxSize(),
            )
        }

        FleetRouteLegend(vehicleRoutes = result.vehicleRoutes, modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp))

        StatStrip(
            vehiclesUsed = result.vehicleRoutes.size,
            totalDistanceMeters = result.totalDistanceMeters,
            totalDurationSeconds = result.totalDurationSeconds,
            totalEstimatedCost = result.totalEstimatedCost,
            modifier = Modifier.fillMaxWidth(),
        )

        LazyColumn(
            modifier = Modifier.weight(1f).fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            itemsIndexed(result.vehicleRoutes) { index, route ->
                VehicleRouteCard(index = index, route = route, liveStatus = liveByVehicleIndex[route.vehicleIndex])
            }
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
private fun StatStrip(
    vehiclesUsed: Int,
    totalDistanceMeters: Double,
    totalDurationSeconds: Double,
    totalEstimatedCost: Double,
    modifier: Modifier = Modifier,
) {
    LazyRow(
        modifier = modifier.padding(horizontal = 16.dp, vertical = 4.dp),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        item { StatCard(icon = Icons.Filled.LocalShipping, label = "Vehicles used", value = vehiclesUsed.toString()) }
        item { StatCard(icon = Icons.Filled.Route, label = "Total distance", value = formatDistance(totalDistanceMeters)) }
        item { StatCard(icon = Icons.Filled.Schedule, label = "Total time", value = formatDuration(totalDurationSeconds)) }
        item { StatCard(icon = Icons.Filled.Payments, label = "Est. cost", value = String.format(Locale.getDefault(), "%.2f", totalEstimatedCost)) }
    }
}

@Composable
private fun StatCard(icon: androidx.compose.ui.graphics.vector.ImageVector, label: String, value: String) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        modifier = Modifier.width(120.dp),
    ) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
            Text(text = value, style = MaterialTheme.typography.titleMedium)
            Text(text = label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun VehicleRouteCard(index: Int, route: VehicleRouteResult, liveStatus: VehicleTrackingStatus?) {
    val vehicleColor = Color(android.graphics.Color.parseColor(colorForVehicle(index)))
    val utilization = route.capacityUtilization.coerceIn(0.0, 1.0)

    Card(shape = RoundedCornerShape(16.dp), modifier = Modifier.fillMaxWidth()) {
        Row(modifier = Modifier.fillMaxWidth()) {
            // A colored accent bar ties this card back to its map route and legend entry at a
            // glance, without needing to read the vehicle number.
            Box(modifier = Modifier.width(6.dp).fillMaxHeight().background(vehicleColor))

            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Box(
                        modifier = Modifier.size(34.dp).background(vehicleColor, CircleShape),
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(Icons.Filled.LocalShipping, contentDescription = null, tint = Color.White, modifier = Modifier.size(18.dp))
                    }
                    Text(
                        text = "Vehicle ${index + 1} — ${route.vehicleType}",
                        style = MaterialTheme.typography.titleMedium,
                        modifier = Modifier.weight(1f),
                    )
                    Text(
                        text = "${route.destinationIndices.size} stop(s)",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }

                route.trackingCode?.let { code ->
                    CopyableIdRow(label = "Driver code", value = code, modifier = Modifier.fillMaxWidth())
                }

                StopTimeline(stopNames = route.stopNames, vehicleColor = vehicleColor)

                Row(horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                    IconMetric(Icons.Filled.Route, formatDistance(route.distanceMeters))
                    IconMetric(Icons.Filled.Schedule, formatDuration(route.durationSeconds))
                    IconMetric(Icons.Filled.Payments, String.format(Locale.getDefault(), "%.2f", route.estimatedCost))
                }

                if (liveStatus != null) {
                    LiveStatusRow(liveStatus = liveStatus, vehicleColor = vehicleColor)
                }

                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(
                            text = "Load: ${route.load.roundToInt()} / ${route.capacity.roundToInt()}",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                        Text(
                            text = "${(utilization * 100).roundToInt()}%",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    LinearProgressIndicator(
                        progress = { utilization.toFloat() },
                        modifier = Modifier.fillMaxWidth(),
                        color = if (utilization > 0.9) MaterialTheme.colorScheme.error else vehicleColor,
                        trackColor = MaterialTheme.colorScheme.surfaceVariant,
                    )
                }

                if (route.timeWindowViolations.isNotEmpty()) {
                    Row(
                        verticalAlignment = Alignment.Top,
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        modifier = Modifier.background(
                            MaterialTheme.colorScheme.errorContainer,
                            RoundedCornerShape(10.dp),
                        ).padding(8.dp),
                    ) {
                        Icon(
                            Icons.Filled.Warning,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.onErrorContainer,
                            modifier = Modifier.size(16.dp),
                        )
                        Text(
                            text = route.timeWindowViolations.joinToString("; "),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onErrorContainer,
                        )
                    }
                }
            }
        }
    }
}

/** This vehicle's live status - present once its driver has opened the Drivers page and reported
 * at least one location. Distinct green "on route" vs. red "off route" coloring mirrors the map's
 * marker coloring for the same vehicle. */
@Composable
private fun LiveStatusRow(liveStatus: VehicleTrackingStatus, vehicleColor: Color) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        modifier = Modifier
            .background(
                if (liveStatus.isOffRoute) MaterialTheme.colorScheme.errorContainer else vehicleColor.copy(alpha = 0.14f),
                RoundedCornerShape(10.dp),
            )
            .padding(8.dp),
    ) {
        Icon(
            if (liveStatus.isOffRoute) Icons.Filled.Warning else Icons.Filled.LocationOn,
            contentDescription = null,
            tint = if (liveStatus.isOffRoute) MaterialTheme.colorScheme.onErrorContainer else vehicleColor,
            modifier = Modifier.size(16.dp),
        )
        Text(
            text = if (liveStatus.isOffRoute) {
                "Off planned route - travelled ${formatDistance(liveStatus.distanceTravelledMeters)} so far"
            } else {
                "Live: travelled ${formatDistance(liveStatus.distanceTravelledMeters)} so far"
            },
            style = MaterialTheme.typography.labelMedium,
            color = if (liveStatus.isOffRoute) MaterialTheme.colorScheme.onErrorContainer else MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

/** The visit order as a horizontally-scrollable row of numbered stops, matching the numbered
 * markers on the map, instead of a single long "A → B → C" line of text that wraps unpredictably
 * and loses the numbering. */
@Composable
private fun StopTimeline(stopNames: List<String>, vehicleColor: Color) {
    LazyRow(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        itemsIndexed(stopNames) { position, name ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (position > 0) {
                    Text(
                        text = "→",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(horizontal = 2.dp),
                    )
                }
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(4.dp),
                    modifier = Modifier
                        .background(vehicleColor.copy(alpha = 0.14f), RoundedCornerShape(20.dp))
                        .padding(horizontal = 8.dp, vertical = 4.dp),
                ) {
                    Box(
                        modifier = Modifier.size(16.dp).background(vehicleColor, CircleShape),
                        contentAlignment = Alignment.Center,
                    ) {
                        Text(text = "${position + 1}", style = MaterialTheme.typography.labelSmall.copy(fontSize = 9.sp), color = Color.White)
                    }
                    Text(text = name, style = MaterialTheme.typography.labelMedium)
                }
            }
        }
    }
}

/** A short id (driver tracking code, or the fleet's session id) with a copy button - these are
 * meant to be handed off to someone else (a driver, an administrator) via whatever channel is
 * convenient (a text, a call), not typed in from this screen. */
@Composable
private fun CopyableIdRow(label: String, value: String, modifier: Modifier = Modifier) {
    val clipboard = LocalClipboardManager.current
    Row(
        modifier = modifier
            .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(10.dp))
            .padding(start = 12.dp, end = 4.dp, top = 4.dp, bottom = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Column {
            Text(text = label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(text = value, style = MaterialTheme.typography.titleSmall)
        }
        IconButton(onClick = { clipboard.setText(AnnotatedString(value)) }) {
            Icon(Icons.Filled.ContentCopy, contentDescription = "Copy $label")
        }
    }
}

@Composable
private fun IconMetric(icon: androidx.compose.ui.graphics.vector.ImageVector, value: String) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(16.dp))
        Text(text = value, style = MaterialTheme.typography.bodyMedium)
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
