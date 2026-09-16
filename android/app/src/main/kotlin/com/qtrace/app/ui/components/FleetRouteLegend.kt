package com.qtrace.app.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.qtrace.app.domain.model.VehicleRouteResult

/** One colored dot per vehicle route, matching MapLibreFleetMap's palette (spec section 10 -
 * "provide a vehicle legend"). */
@Composable
fun FleetRouteLegend(vehicleRoutes: List<VehicleRouteResult>, modifier: Modifier = Modifier) {
    LazyRow(modifier = modifier, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        itemsIndexed(vehicleRoutes) { index, route ->
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Surface(
                    modifier = Modifier.size(12.dp),
                    shape = CircleShape,
                    color = Color(android.graphics.Color.parseColor(colorForVehicle(index))),
                ) {}
                Text(
                    text = "Vehicle ${index + 1} — ${route.vehicleType}",
                    style = MaterialTheme.typography.labelMedium,
                )
            }
        }
    }
}
