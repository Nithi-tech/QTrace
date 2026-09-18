package com.qtrace.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.qtrace.app.R

private data class LegendEntry(val color: Color, val labelRes: Int)

/** QTrace's own 5-level traffic scale, matching the exact colors MapLibreRouteMap draws
 * (CLAUDE.md traffic master-prompt #15) - real UI swatches, not emoji. */
private val LEGEND_ENTRIES = listOf(
    LegendEntry(Color(0xFF2E7D32), R.string.traffic_level_free_flow),
    LegendEntry(Color(0xFFF9A825), R.string.traffic_level_moderate),
    LegendEntry(Color(0xFFEF6C00), R.string.traffic_level_heavy),
    LegendEntry(Color(0xFFD32F2F), R.string.traffic_level_very_heavy),
    LegendEntry(Color(0xFF6A1B1A), R.string.traffic_level_severe),
)

@Composable
fun TrafficLegend(modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.surface.copy(alpha = 0.92f),
        tonalElevation = 3.dp,
    ) {
        Column(modifier = Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                text = stringResource(R.string.traffic_legend_title),
                style = MaterialTheme.typography.labelMedium,
            )
            LEGEND_ENTRIES.forEach { entry ->
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    androidx.compose.foundation.Canvas(modifier = Modifier.size(width = 18.dp, height = 4.dp)) {
                        drawRect(color = entry.color)
                    }
                    Text(text = stringResource(entry.labelRes), style = MaterialTheme.typography.labelSmall)
                }
            }
        }
    }
}
