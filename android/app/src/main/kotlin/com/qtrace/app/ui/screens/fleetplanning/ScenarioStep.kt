package com.qtrace.app.ui.screens.fleetplanning

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.qtrace.app.domain.model.ScenarioType

/** Spec section 1: "What type of transportation do you want to optimize?" - clean, modern
 * selectable cards, one per scenario. The selection controls which inputs later steps show. */
@Composable
fun ScenarioStep(state: FleetPlanningState, onEvent: (FleetPlanningEvent) -> Unit) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            text = "What type of transportation do you want to optimize?",
            style = MaterialTheme.typography.titleMedium,
        )

        ScenarioType.entries.forEach { scenario ->
            val selected = state.scenario == scenario
            Card(
                onClick = { onEvent(FleetPlanningEvent.ScenarioSelected(scenario)) },
                colors = CardDefaults.cardColors(
                    containerColor = if (selected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant,
                ),
                modifier = Modifier.fillMaxWidth(),
            ) {
                androidx.compose.foundation.layout.Row(
                    modifier = Modifier.fillMaxWidth().padding(16.dp),
                    verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
                ) {
                    RadioButton(selected = selected, onClick = { onEvent(FleetPlanningEvent.ScenarioSelected(scenario)) })
                    Column(modifier = Modifier.padding(start = 8.dp)) {
                        Text(text = scenario.displayName, style = MaterialTheme.typography.titleMedium)
                        Text(
                            text = scenario.exampleText,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }
    }
}
