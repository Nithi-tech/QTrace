package com.qtrace.app.ui.screens.fleetplanning

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.qtrace.app.domain.model.Coordinate
import com.qtrace.app.domain.model.LocationSuggestion
import com.qtrace.app.ui.components.LocationSearchField

/** Spec section 2: depot/warehouse/start location, treated as the VRP's fixed starting node. */
@Composable
fun DepotStep(state: FleetPlanningState, onEvent: (FleetPlanningEvent) -> Unit) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(text = "Where do vehicles start from?", style = MaterialTheme.typography.titleMedium)

        LocationSearchField(
            label = "Depot / Warehouse",
            query = state.depotQuery,
            suggestions = state.depotSuggestions,
            isExpanded = state.depotSuggestions.isNotEmpty(),
            isSearching = state.isSearchingDepot,
            onQueryChanged = { onEvent(FleetPlanningEvent.DepotQueryChanged(it)) },
            onFocused = { onEvent(FleetPlanningEvent.DepotFieldFocused) },
            onDismiss = { onEvent(FleetPlanningEvent.DepotSuggestionsDismissed) },
            onSuggestionSelected = { onEvent(FleetPlanningEvent.DepotSelected(it)) },
            onClear = { onEvent(FleetPlanningEvent.ClearDepot) },
            placeholder = "Search location",
            modifier = Modifier.fillMaxWidth(),
        )

        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(
                checked = state.returnToDepot,
                onCheckedChange = { onEvent(FleetPlanningEvent.ReturnToDepotToggled(it)) },
            )
            Text("Vehicles return to depot")
        }

        ManualCoordinateFallback(onEvent = onEvent)
    }
}

/** Fallback for when address search is unavailable (no geocoding provider configured, or
 * offline) - lets the depot still be set directly by coordinates. */
@Composable
private fun ManualCoordinateFallback(onEvent: (FleetPlanningEvent) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    var latitude by remember { mutableStateOf("") }
    var longitude by remember { mutableStateOf("") }

    TextButton(onClick = { expanded = !expanded }) {
        Text(if (expanded) "Hide manual coordinates" else "Or enter coordinates manually")
    }

    if (expanded) {
        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = latitude,
                    onValueChange = { latitude = it },
                    label = { Text("Latitude") },
                    singleLine = true,
                    keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    modifier = Modifier.weight(1f),
                )
                OutlinedTextField(
                    value = longitude,
                    onValueChange = { longitude = it },
                    label = { Text("Longitude") },
                    singleLine = true,
                    keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    modifier = Modifier.weight(1f),
                )
            }
            OutlinedButton(
                onClick = {
                    val lat = latitude.toDoubleOrNull()
                    val lon = longitude.toDoubleOrNull()
                    if (lat != null && lon != null) {
                        val coordinate = runCatching { Coordinate(lat, lon) }.getOrNull()
                        if (coordinate != null) {
                            onEvent(
                                FleetPlanningEvent.DepotSelected(
                                    LocationSuggestion(label = "($lat, $lon)", coordinate = coordinate),
                                ),
                            )
                        }
                    }
                },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Use these coordinates")
            }
        }
    }
}
