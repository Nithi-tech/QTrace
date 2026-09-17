package com.qtrace.app.ui.screens.routeplanning

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.qtrace.app.BuildConfig
import com.qtrace.app.R
import com.qtrace.app.ui.components.ErrorBanner
import com.qtrace.app.ui.components.LocationSearchField
import com.qtrace.app.ui.components.MapLibreRouteMap
import com.qtrace.app.ui.components.OfflineBanner
import com.qtrace.app.ui.components.RouteResultPanel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RoutePlanningScreen(
    onNavigateToFleetPlanning: () -> Unit = {},
    onNavigateToDriverTracking: () -> Unit = {},
    onNavigateToAdminTracking: () -> Unit = {},
    viewModel: RoutePlanningViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()

    Scaffold { paddingValues ->
        Column(modifier = Modifier.fillMaxSize().padding(paddingValues)) {
            Header(
                onNavigateToFleetPlanning = onNavigateToFleetPlanning,
                onNavigateToDriverTracking = onNavigateToDriverTracking,
                onNavigateToAdminTracking = onNavigateToAdminTracking,
            )

            RoutePlanningInputs(state = state, onEvent = viewModel::onEvent)

            if (state.isOffline) {
                OfflineBanner(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp))
            }
            state.error?.let { error ->
                ErrorBanner(
                    error = error,
                    onRetry = { viewModel.onEvent(RoutePlanningEvent.RetryClicked) },
                    onDismiss = { viewModel.onEvent(RoutePlanningEvent.ErrorDismissed) },
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
                )
            }

            Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
                MapLibreRouteMap(
                    styleUrl = BuildConfig.MAP_STYLE_URL,
                    startLocation = state.startLocation?.coordinate,
                    destinationLocation = state.destinationLocation?.coordinate,
                    routeGeometry = state.optimizationResult?.route?.geometry.orEmpty(),
                    modifier = Modifier.fillMaxSize(),
                )

                if (state.isPlanningRoute) {
                    Surface(
                        modifier = Modifier.align(Alignment.Center).padding(16.dp),
                        shape = MaterialTheme.shapes.medium,
                        tonalElevation = 4.dp,
                    ) {
                        Row {
                            CircularProgressIndicator(modifier = Modifier.padding(16.dp))
                            Text(
                                text = stringResource(R.string.loading_optimizing),
                                modifier = Modifier.align(Alignment.CenterVertically).padding(end = 16.dp),
                            )
                        }
                    }
                }
            }

            state.optimizationResult?.let { result ->
                RouteResultPanel(result = result, modifier = Modifier.padding(16.dp))
            }

            Button(
                onClick = { viewModel.onEvent(RoutePlanningEvent.OptimizeRouteClicked) },
                enabled = state.canOptimize,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
            ) {
                Text(stringResource(R.string.optimize_route_action))
            }
        }
    }
}

@Composable
private fun Header(
    onNavigateToFleetPlanning: () -> Unit,
    onNavigateToDriverTracking: () -> Unit,
    onNavigateToAdminTracking: () -> Unit,
) {
    Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 12.dp)) {
        Column {
            Text(text = stringResource(R.string.app_name), style = MaterialTheme.typography.headlineSmall)
            Text(
                text = stringResource(R.string.app_tagline),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
            TextButton(onClick = onNavigateToFleetPlanning) {
                Text(stringResource(R.string.fleet_planning_action))
            }
            TextButton(onClick = onNavigateToDriverTracking) {
                Text(stringResource(R.string.driver_tracking_action))
            }
            TextButton(onClick = onNavigateToAdminTracking) {
                Text(stringResource(R.string.admin_tracking_action))
            }
        }
    }
}

@Composable
private fun RoutePlanningInputs(state: RoutePlanningState, onEvent: (RoutePlanningEvent) -> Unit) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        LocationSearchField(
            label = stringResource(R.string.start_location_label),
            query = state.startQuery,
            suggestions = state.startSuggestions,
            isExpanded = state.activeSuggestionField == ActiveSuggestionField.START,
            isSearching = state.isSearchingStart,
            onQueryChanged = { onEvent(RoutePlanningEvent.StartQueryChanged(it)) },
            onFocused = { onEvent(RoutePlanningEvent.StartFieldFocused) },
            onDismiss = { onEvent(RoutePlanningEvent.SuggestionsDismissed) },
            onSuggestionSelected = { onEvent(RoutePlanningEvent.StartLocationSelected(it)) },
            onClear = { onEvent(RoutePlanningEvent.ClearStartLocation) },
            placeholder = stringResource(R.string.start_location_placeholder),
            modifier = Modifier.fillMaxWidth(),
        )

        LocationSearchField(
            label = stringResource(R.string.destination_label),
            query = state.destinationQuery,
            suggestions = state.destinationSuggestions,
            isExpanded = state.activeSuggestionField == ActiveSuggestionField.DESTINATION,
            isSearching = state.isSearchingDestination,
            onQueryChanged = { onEvent(RoutePlanningEvent.DestinationQueryChanged(it)) },
            onFocused = { onEvent(RoutePlanningEvent.DestinationFieldFocused) },
            onDismiss = { onEvent(RoutePlanningEvent.SuggestionsDismissed) },
            onSuggestionSelected = { onEvent(RoutePlanningEvent.DestinationLocationSelected(it)) },
            onClear = { onEvent(RoutePlanningEvent.ClearDestinationLocation) },
            placeholder = stringResource(R.string.destination_placeholder),
            modifier = Modifier.fillMaxWidth(),
        )

        if (state.isSameLocationSelected) {
            Text(
                text = stringResource(R.string.error_same_location),
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.error,
            )
        }
    }
}
