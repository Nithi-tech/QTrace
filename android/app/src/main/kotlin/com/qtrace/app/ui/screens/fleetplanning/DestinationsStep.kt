package com.qtrace.app.ui.screens.fleetplanning

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
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

/** Spec section 4: CSV upload plus manual entry. Coordinates are optional per row - the backend
 * geocodes any destination given only a name/address (CLAUDE.md: reuse existing geocoding). */
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

        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.weight(1f, fill = false)) {
            items(state.destinations, key = { it.id }) { destination ->
                DestinationRow(destination = destination, onEvent = onEvent)
            }
        }

        OutlinedButton(onClick = { onEvent(FleetPlanningEvent.AddDestination) }, modifier = Modifier.fillMaxWidth()) {
            Icon(Icons.Filled.Add, contentDescription = null)
            Text(" Add Destination Manually")
        }
    }
}

@Composable
private fun DestinationRow(destination: DestinationInput, onEvent: (FleetPlanningEvent) -> Unit) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                OutlinedTextField(
                    value = destination.name,
                    onValueChange = {
                        onEvent(FleetPlanningEvent.DestinationFieldChanged(destination.id, DestinationField.NAME, it))
                    },
                    label = { Text("Name / address") },
                    singleLine = true,
                    modifier = Modifier.weight(1f),
                )
                IconButton(onClick = { onEvent(FleetPlanningEvent.RemoveDestination(destination.id)) }) {
                    Icon(Icons.Filled.Delete, contentDescription = "Remove destination")
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = destination.demand,
                    onValueChange = {
                        onEvent(FleetPlanningEvent.DestinationFieldChanged(destination.id, DestinationField.DEMAND, it))
                    },
                    label = { Text("Demand") },
                    singleLine = true,
                    keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = KeyboardType.Number),
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
                    keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier.weight(1f),
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = destination.latitude,
                    onValueChange = {
                        onEvent(FleetPlanningEvent.DestinationFieldChanged(destination.id, DestinationField.LATITUDE, it))
                    },
                    label = { Text("Latitude (optional)") },
                    singleLine = true,
                    keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    modifier = Modifier.weight(1f),
                )
                OutlinedTextField(
                    value = destination.longitude,
                    onValueChange = {
                        onEvent(FleetPlanningEvent.DestinationFieldChanged(destination.id, DestinationField.LONGITUDE, it))
                    },
                    label = { Text("Longitude (optional)") },
                    singleLine = true,
                    keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = KeyboardType.Decimal),
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
        }
    }
}
