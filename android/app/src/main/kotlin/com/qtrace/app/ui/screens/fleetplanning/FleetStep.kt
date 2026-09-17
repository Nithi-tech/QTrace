package com.qtrace.app.ui.screens.fleetplanning

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
import androidx.compose.material3.Card
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.qtrace.app.domain.model.ScenarioType

/** Spec section 3: multiple vehicle types and quantities, each with capacity/cost/availability -
 * the whole fleet is what the optimizer assigns destinations across (spec section 7). */
@Composable
fun FleetStep(state: FleetPlanningState, onEvent: (FleetPlanningEvent) -> Unit) {
    Column(modifier = Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(text = "Configure your available fleet", style = MaterialTheme.typography.titleMedium)
        Text(
            text = "Capacity units: ${capacityHint(state.scenario)}",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.weight(1f, fill = false)) {
            items(state.vehicles, key = { it.id }) { vehicle ->
                VehicleRow(vehicle = vehicle, onEvent = onEvent)
            }
        }

        OutlinedButton(onClick = { onEvent(FleetPlanningEvent.AddVehicle) }, modifier = Modifier.fillMaxWidth()) {
            Icon(Icons.Filled.Add, contentDescription = null)
            Text(" Add Vehicle")
        }
    }
}

@Composable
private fun VehicleRow(vehicle: VehicleSpecInput, onEvent: (FleetPlanningEvent) -> Unit) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                OutlinedTextField(
                    value = vehicle.vehicleType,
                    onValueChange = { onEvent(FleetPlanningEvent.VehicleFieldChanged(vehicle.id, VehicleField.TYPE, it)) },
                    label = { Text("Vehicle type") },
                    placeholder = { Text("Van, Mini Truck, Bus...") },
                    singleLine = true,
                    modifier = Modifier.weight(1f),
                )
                IconButton(onClick = { onEvent(FleetPlanningEvent.RemoveVehicle(vehicle.id)) }) {
                    Icon(Icons.Filled.Delete, contentDescription = "Remove vehicle")
                }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                NumberField(
                    value = vehicle.count,
                    label = "Number",
                    onValueChange = { onEvent(FleetPlanningEvent.VehicleFieldChanged(vehicle.id, VehicleField.COUNT, it)) },
                    modifier = Modifier.weight(1f),
                    placeholder = "1",
                )
                NumberField(
                    value = vehicle.capacity,
                    label = "Capacity",
                    onValueChange = { onEvent(FleetPlanningEvent.VehicleFieldChanged(vehicle.id, VehicleField.CAPACITY, it)) },
                    modifier = Modifier.weight(1f),
                )
                NumberField(
                    value = vehicle.costPerKm,
                    label = "Cost/km",
                    onValueChange = { onEvent(FleetPlanningEvent.VehicleFieldChanged(vehicle.id, VehicleField.COST_PER_KM, it)) },
                    modifier = Modifier.weight(1f),
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = vehicle.availabilityStart,
                    onValueChange = {
                        onEvent(FleetPlanningEvent.VehicleFieldChanged(vehicle.id, VehicleField.AVAILABILITY_START, it))
                    },
                    label = { Text("Available from") },
                    placeholder = { Text("08:00") },
                    singleLine = true,
                    modifier = Modifier.weight(1f),
                )
                OutlinedTextField(
                    value = vehicle.availabilityEnd,
                    onValueChange = {
                        onEvent(FleetPlanningEvent.VehicleFieldChanged(vehicle.id, VehicleField.AVAILABILITY_END, it))
                    },
                    label = { Text("Available until") },
                    placeholder = { Text("18:00") },
                    singleLine = true,
                    modifier = Modifier.weight(1f),
                )
            }
        }
    }
}

@Composable
private fun NumberField(
    value: String,
    label: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    placeholder: String? = null,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        placeholder = placeholder?.let { { Text(it) } },
        singleLine = true,
        keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = KeyboardType.Number),
        modifier = modifier,
    )
}

private fun capacityHint(scenario: ScenarioType?): String = when (scenario) {
    ScenarioType.PASSENGER_TRANSPORT -> "number of passengers"
    ScenarioType.PACKAGE_DELIVERY, ScenarioType.GOODS_LOGISTICS, null -> "kg (or your chosen load unit)"
}
