package com.qtrace.app.ui.screens.driver

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.LocationManager
import android.os.Looper
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import androidx.hilt.navigation.compose.hiltViewModel
import com.qtrace.app.BuildConfig
import com.qtrace.app.R
import com.qtrace.app.domain.model.AssignedRoute
import com.qtrace.app.domain.model.Coordinate
import com.qtrace.app.domain.model.VehicleRouteResult
import com.qtrace.app.ui.components.ErrorBanner
import com.qtrace.app.ui.components.FleetStopMarker
import com.qtrace.app.ui.components.MapLibreFleetMap
import java.util.Locale
import kotlin.math.roundToInt

/** A driver enters their tracking code to see their assigned route and start reporting their
 * live location - Google-Maps-style: the planned path on a map, their own position on it, and a
 * checklist of stops in visit order. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DriverTrackingScreen(onExit: () -> Unit, viewModel: DriverTrackingViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current

    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        viewModel.onEvent(DriverTrackingEvent.LocationPermissionResult(granted))
    }

    LaunchedEffect(state.step) {
        if (state.step == DriverTrackingStep.TRACKING) {
            if (hasLocationPermission(context)) {
                viewModel.onEvent(DriverTrackingEvent.LocationPermissionResult(true))
            } else {
                permissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
            }
        }
    }

    if (state.step == DriverTrackingStep.TRACKING && state.locationPermissionGranted) {
        DriverLocationUpdates(onLocationUpdated = { viewModel.onEvent(DriverTrackingEvent.LocationUpdated(it)) })
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Driver") },
                navigationIcon = {
                    IconButton(onClick = {
                        if (state.step == DriverTrackingStep.TRACKING) {
                            viewModel.onEvent(DriverTrackingEvent.StopTrackingClicked)
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
                    onRetry = { viewModel.onEvent(DriverTrackingEvent.RetryClicked) },
                    onDismiss = { viewModel.onEvent(DriverTrackingEvent.ErrorDismissed) },
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
                )
            }

            when (state.step) {
                DriverTrackingStep.CODE_ENTRY -> CodeEntryContent(state, viewModel::onEvent)
                DriverTrackingStep.TRACKING -> state.assignedRoute?.let { route ->
                    TrackingContent(
                        route = route,
                        currentLocation = state.currentLocation,
                        distanceTravelledMeters = state.distanceTravelledMeters,
                        locationPermissionGranted = state.locationPermissionGranted,
                        lastPingFailed = state.lastPingFailed,
                    )
                }
            }
        }
    }
}

@Composable
private fun CodeEntryContent(state: DriverTrackingState, onEvent: (DriverTrackingEvent) -> Unit) {
    Column(modifier = Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(text = "Enter your tracking code", style = MaterialTheme.typography.titleMedium)
        Text(
            text = "Your dispatcher gives you this code after generating routes for your fleet.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        OutlinedTextField(
            value = state.codeInput,
            onValueChange = { onEvent(DriverTrackingEvent.CodeInputChanged(it)) },
            label = { Text("Tracking code") },
            placeholder = { Text("e.g. ABC123") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Button(
            onClick = { onEvent(DriverTrackingEvent.StartTrackingClicked) },
            enabled = state.canStartTracking,
            modifier = Modifier.fillMaxWidth(),
        ) {
            if (state.isLoading) {
                CircularProgressIndicator(modifier = Modifier.padding(end = 8.dp))
            }
            Text("Start Tracking")
        }
    }
}

@Composable
private fun TrackingContent(
    route: AssignedRoute,
    currentLocation: Coordinate?,
    distanceTravelledMeters: Double,
    locationPermissionGranted: Boolean,
    lastPingFailed: Boolean,
) {
    val fakeRoute = VehicleRouteResult(
        vehicleIndex = 0,
        vehicleType = route.vehicleType,
        stopNames = route.stopNames,
        destinationIndices = emptyList(),
        distanceMeters = route.distanceMeters,
        durationSeconds = route.durationSeconds,
        load = 0.0,
        capacity = 0.0,
        capacityUtilization = 0.0,
        estimatedCost = 0.0,
        timeWindowViolations = emptyList(),
        geometry = route.geometry,
    )

    Column(modifier = Modifier.fillMaxSize()) {
        if (!locationPermissionGranted) {
            Card(modifier = Modifier.fillMaxWidth().padding(16.dp)) {
                Text(
                    text = "Location permission is needed to share your position with dispatch.",
                    modifier = Modifier.padding(12.dp),
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        } else if (lastPingFailed) {
            Card(
                colors = androidx.compose.material3.CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
                modifier = Modifier.fillMaxWidth().padding(16.dp),
            ) {
                Text(
                    text = "Couldn't reach dispatch with your last location update - will keep retrying.",
                    modifier = Modifier.padding(12.dp),
                    color = MaterialTheme.colorScheme.onErrorContainer,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }

        Box(modifier = Modifier.weight(1.2f).fillMaxWidth()) {
            MapLibreFleetMap(
                styleUrl = BuildConfig.MAP_STYLE_URL,
                depot = null,
                destinationMarkers = currentLocation?.let { listOf(FleetStopMarker(coordinate = it, vehicleIndex = 0)) }.orEmpty(),
                vehicleRoutes = listOf(fakeRoute),
                modifier = Modifier.fillMaxSize(),
            )
        }

        Row(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(24.dp),
        ) {
            Column {
                Text("Planned distance", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text(formatDistance(route.distanceMeters), style = MaterialTheme.typography.titleSmall)
            }
            Column {
                Text("Travelled so far", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Text(formatDistance(distanceTravelledMeters), style = MaterialTheme.typography.titleSmall)
            }
        }

        Text(
            text = "Stops",
            style = MaterialTheme.typography.titleSmall,
            modifier = Modifier.padding(horizontal = 16.dp),
        )
        LazyColumn(modifier = Modifier.weight(1f).fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            itemsIndexed(route.stopNames) { index, name ->
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(text = "${index + 1}.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(text = name, style = MaterialTheme.typography.bodyMedium)
                }
            }
        }
    }
}

private fun hasLocationPermission(context: Context): Boolean =
    ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED

/** Registers a plain android.location.LocationManager listener for the lifetime this composable
 * is in the composition (no play-services-location dependency needed for this - CLAUDE.md #32). */
@Composable
private fun DriverLocationUpdates(onLocationUpdated: (Coordinate) -> Unit) {
    val context = LocalContext.current
    DisposableEffect(Unit) {
        val locationManager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        val listener = android.location.LocationListener { location ->
            onLocationUpdated(Coordinate(latitude = location.latitude, longitude = location.longitude))
        }
        val provider = when {
            locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER) -> LocationManager.GPS_PROVIDER
            locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER) -> LocationManager.NETWORK_PROVIDER
            else -> null
        }
        if (provider != null) {
            try {
                locationManager.requestLocationUpdates(provider, 10_000L, 15f, listener, Looper.getMainLooper())
            } catch (_: SecurityException) {
                // Permission was revoked in the moment between the check and this call; the
                // driver simply won't see live tracking until they grant it again.
            }
        }
        onDispose { locationManager.removeUpdates(listener) }
    }
}

private fun formatDistance(meters: Double): String =
    if (meters >= 1000) String.format(Locale.getDefault(), "%.1f km", meters / 1000.0) else "${meters.roundToInt()} m"
