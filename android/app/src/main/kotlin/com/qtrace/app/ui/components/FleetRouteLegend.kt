package com.qtrace.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.qtrace.app.domain.model.VehicleRouteResult

/** One filled, colored chip per vehicle route - matching MapLibreFleetMap's palette and each
 * route card's accent color - so identifying a vehicle on the map, in this legend, and in its
 * route card below is one consistent color, not three different visual languages. */
@Composable
fun FleetRouteLegend(vehicleRoutes: List<VehicleRouteResult>, modifier: Modifier = Modifier) {
    LazyRow(modifier = modifier, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        itemsIndexed(vehicleRoutes) { index, route ->
            val color = Color(android.graphics.Color.parseColor(colorForVehicle(index)))
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                modifier = Modifier
                    .background(color.copy(alpha = 0.16f), RoundedCornerShape(20.dp))
                    .padding(horizontal = 10.dp, vertical = 6.dp),
            ) {
                Surface(modifier = Modifier.size(10.dp), shape = CircleShape, color = color) {}
                Text(
                    text = "Vehicle ${index + 1} — ${route.vehicleType} (${route.destinationIndices.size} stop(s))",
                    style = MaterialTheme.typography.labelMedium,
                )
            }
        }
    }
}
