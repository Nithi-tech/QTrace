package com.qtrace.app.ui.screens.fleetplanning

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.qtrace.app.domain.model.LocationSuggestion
import com.qtrace.app.ui.components.LocationSearchField
import com.qtrace.app.ui.components.ManualCoordinateEntry

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
        if (state.depot != null) {
            Text(
                text = "✓ Location confirmed",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.primary,
            )
        }

        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(
                checked = state.returnToDepot,
                onCheckedChange = { onEvent(FleetPlanningEvent.ReturnToDepotToggled(it)) },
            )
            Text("Vehicles return to depot")
        }

        ManualCoordinateEntry { coordinate ->
            onEvent(FleetPlanningEvent.DepotSelected(LocationSuggestion(label = "(${coordinate.latitude}, ${coordinate.longitude})", coordinate = coordinate)))
        }
    }
}
