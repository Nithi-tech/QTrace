package com.qtrace.app.ui.screens.fleetplanning

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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.LocalShipping
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
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.qtrace.app.domain.model.ScenarioType
import com.qtrace.app.ui.components.colorForVehicle
import kotlin.math.ceil

/** Multiple vehicle types and quantities, each with capacity/cost/availability - the whole fleet
 * is what the optimizer assigns destinations across. This step now comes after Destinations
 * (see [FleetPlanningStep]), so the destinations' total demand is already known and each
 * vehicle's Number field can suggest how many are actually needed at that capacity, instead of
 * asking the user to guess a fleet size blind. */
@Composable
fun FleetStep(state: FleetPlanningState, onEvent: (FleetPlanningEvent) -> Unit) {
    Column(modifier = Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(text = "Configure your available fleet", style = MaterialTheme.typography.titleMedium)

        Card(
            shape = RoundedCornerShape(14.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
            modifier = Modifier.fillMaxWidth(),
        ) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                Icon(Icons.Filled.Info, contentDescription = null, tint = MaterialTheme.colorScheme.onPrimaryContainer)
                Text(
                    text = "${state.destinations.size} destination(s) to serve, totaling " +
                        "${formatDemand(state.totalDestinationDemand)} ${capacityHint(state.scenario)}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onPrimaryContainer,
                )
            }
        }

        LazyColumn(verticalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.weight(1f, fill = false)) {
            itemsIndexed(state.vehicles, key = { _, vehicle -> vehicle.id }) { index, vehicle ->
                VehicleRow(index = index, vehicle = vehicle, totalDemand = state.totalDestinationDemand, onEvent = onEvent)
            }
        }

        OutlinedButton(onClick = { onEvent(FleetPlanningEvent.AddVehicle) }, modifier = Modifier.fillMaxWidth()) {
            Icon(Icons.Filled.Add, contentDescription = null)
            Text(" Add Vehicle")
        }
    }
}

@Composable
private fun VehicleRow(
    index: Int,
    vehicle: VehicleSpecInput,
    totalDemand: Double,
    onEvent: (FleetPlanningEvent) -> Unit,
) {
    Card(
        shape = RoundedCornerShape(16.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .background(color = androidx.compose.ui.graphics.Color(android.graphics.Color.parseColor(colorForVehicle(index))), shape = CircleShape),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(Icons.Filled.LocalShipping, contentDescription = null, tint = androidx.compose.ui.graphics.Color.White)
                }
                OutlinedTextField(
                    value = vehicle.vehicleType,
                    onValueChange = { onEvent(FleetPlanningEvent.VehicleFieldChanged(vehicle.id, VehicleField.TYPE, it)) },
                    label = { Text("Vehicle ${index + 1} type") },
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
                    supportingText = suggestedVehicleCount(totalDemand, vehicle.capacity)?.let { "Suggested: $it+" },
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
    supportingText: String? = null,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        placeholder = placeholder?.let { { Text(it) } },
        supportingText = supportingText?.let { { Text(it, style = MaterialTheme.typography.labelSmall) } },
        singleLine = true,
        keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = KeyboardType.Number),
        modifier = modifier,
    )
}

/** Minimum vehicles of this capacity needed to cover the destinations' total demand - a floor,
 * not the optimizer's actual assignment (which also weighs direction and cost), but enough to
 * stop the user under-provisioning the fleet before generating routes. Null when there's nothing
 * to suggest yet (no capacity entered, or no demand on any destination). */
private fun suggestedVehicleCount(totalDemand: Double, capacityInput: String): Int? {
    val capacity = capacityInput.toDoubleOrNull() ?: return null
    if (capacity <= 0.0 || totalDemand <= 0.0) return null
    return ceil(totalDemand / capacity).toInt()
}

private fun formatDemand(demand: Double): String =
    if (demand == demand.toLong().toDouble()) demand.toLong().toString() else demand.toString()

private fun capacityHint(scenario: ScenarioType?): String = when (scenario) {
    ScenarioType.PASSENGER_TRANSPORT -> "passenger(s)"
    ScenarioType.PACKAGE_DELIVERY, ScenarioType.GOODS_LOGISTICS, null -> "kg (or your chosen load unit)"
}
