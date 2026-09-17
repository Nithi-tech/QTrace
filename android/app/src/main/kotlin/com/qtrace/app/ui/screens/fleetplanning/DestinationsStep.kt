package com.qtrace.app.ui.screens.fleetplanning

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.UploadFile
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.qtrace.app.ui.components.LocationSearchField
import com.qtrace.app.ui.components.ManualCoordinateEntry

/**
 * Spec section 4: CSV upload plus manual entry. Each manually-added destination now searches
 * and confirms a real place via [LocationSearchField] - the same reliable pattern the depot
 * field already used - instead of sending a bare typed name to the backend and hoping its
 * geocoder resolves it correctly (the exact issue reported: "the name alone can't correctly
 * determine" the location). A destination without a confirmed coordinate is still allowed
 * through as an address for the backend to attempt (useful for CSV-imported rows that can't
 * realistically be confirmed one-by-one), but the UI now makes clear which rows are confirmed
 * and which aren't (see [DestinationRow]'s confirmation indicator).
 */
@Composable
fun DestinationsStep(state: FleetPlanningState, onEvent: (FleetPlanningEvent) -> Unit) {
    val context = LocalContext.current
    val filePicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri == null) return@rememberLauncherForActivityResult
        val content = runCatching {
            context.contentResolver.openInputStream(uri)?.bufferedReader()?.use { it.readText() }
        }.getOrNull()
        if (content != null) onEvent(FleetPlanningEvent.CsvImported(content))
    }

    Column(modifier = Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(text = "Where are you delivering?", style = MaterialTheme.typography.titleMedium)
        Text(
            text = "Search and select each destination for the most accurate routes.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        OutlinedButton(onClick = { filePicker.launch("text/*") }, modifier = Modifier.fillMaxWidth()) {
            Icon(Icons.Filled.UploadFile, contentDescription = null)
            Text(" Upload CSV (name, demand, time window, service time)")
        }

        state.csvImportError?.let { message ->
            Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
                Row(modifier = Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = message,
                        color = MaterialTheme.colorScheme.onErrorContainer,
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.weight(1f),
                    )
                    IconButton(onClick = { onEvent(FleetPlanningEvent.CsvImportErrorDismissed) }) {
                        Icon(Icons.Filled.Delete, contentDescription = "Dismiss")
                    }
                }
            }
        }

        Text(text = "${state.destinations.size} destination(s)", style = MaterialTheme.typography.labelMedium)

        LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.weight(1f, fill = false)) {
            itemsIndexed(state.destinations, key = { _, destination -> destination.id }) { index, destination ->
                DestinationRow(index = index, destination = destination, onEvent = onEvent)
            }
        }

        OutlinedButton(onClick = { onEvent(FleetPlanningEvent.AddDestination) }, modifier = Modifier.fillMaxWidth()) {
            Icon(Icons.Filled.Add, contentDescription = null)
            Text(" Add Destination Manually")
        }
    }
}

@Composable
private fun DestinationRow(index: Int, destination: DestinationInput, onEvent: (FleetPlanningEvent) -> Unit) {
    Card(
        shape = RoundedCornerShape(16.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Box(
                    modifier = Modifier
                        .size(28.dp)
                        .background(color = MaterialTheme.colorScheme.secondaryContainer, shape = CircleShape),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(
                        text = "${index + 1}",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSecondaryContainer,
                    )
                }
                LocationSearchField(
                    label = "Destination name / address",
                    query = destination.query,
                    suggestions = destination.suggestions,
                    isExpanded = destination.suggestions.isNotEmpty(),
                    isSearching = destination.isSearching,
                    onQueryChanged = { onEvent(FleetPlanningEvent.DestinationQueryChanged(destination.id, it)) },
                    onFocused = { onEvent(FleetPlanningEvent.DestinationFieldFocused(destination.id)) },
                    onDismiss = { onEvent(FleetPlanningEvent.DestinationSuggestionsDismissed(destination.id)) },
                    onSuggestionSelected = { onEvent(FleetPlanningEvent.DestinationSuggestionSelected(destination.id, it)) },
                    onClear = { onEvent(FleetPlanningEvent.ClearDestinationLocation(destination.id)) },
                    placeholder = "Search for a place",
                    modifier = Modifier.weight(1f),
                )
                IconButton(onClick = { onEvent(FleetPlanningEvent.RemoveDestination(destination.id)) }) {
                    Icon(Icons.Filled.Delete, contentDescription = "Remove destination")
                }
            }

            if (destination.isConfirmed) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        Icons.Filled.CheckCircle,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.padding(end = 4.dp),
                    )
                    Text(
                        text = "Location confirmed",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
            } else if (destination.query.isNotBlank()) {
                Text(
                    text = "Not confirmed - select a suggestion above, or enter coordinates below",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.error,
                )
            }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = destination.demand,
                    onValueChange = {
                        onEvent(FleetPlanningEvent.DestinationFieldChanged(destination.id, DestinationField.DEMAND, it))
                    },
                    label = { Text("Demand") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier.weight(1f),
                )
                OutlinedTextField(
                    value = destination.serviceTimeMinutes,
                    onValueChange = {
                        onEvent(
                            FleetPlanningEvent.DestinationFieldChanged(destination.id, DestinationField.SERVICE_TIME_MINUTES, it),
                        )
                    },
                    label = { Text("Service (min)") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier.weight(1f),
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = destination.timeWindowStart,
                    onValueChange = {
                        onEvent(
                            FleetPlanningEvent.DestinationFieldChanged(destination.id, DestinationField.TIME_WINDOW_START, it),
                        )
                    },
                    label = { Text("Window from") },
                    placeholder = { Text("09:00") },
                    singleLine = true,
                    modifier = Modifier.weight(1f),
                )
                OutlinedTextField(
                    value = destination.timeWindowEnd,
                    onValueChange = {
                        onEvent(
                            FleetPlanningEvent.DestinationFieldChanged(destination.id, DestinationField.TIME_WINDOW_END, it),
                        )
                    },
                    label = { Text("Window until") },
                    placeholder = { Text("11:00") },
                    singleLine = true,
                    modifier = Modifier.weight(1f),
                )
            }

            if (!destination.isConfirmed) {
                ManualCoordinateEntry { coordinate ->
                    onEvent(FleetPlanningEvent.ManualCoordinateEntered(destination.id, coordinate))
                }
            }
        }
    }
}
