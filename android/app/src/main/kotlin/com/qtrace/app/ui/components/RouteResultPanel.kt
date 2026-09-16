package com.qtrace.app.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.qtrace.app.R
import com.qtrace.app.domain.model.OptimizationResult
import java.util.Locale
import kotlin.math.roundToInt

/** Compact result summary (CLAUDE.md spec #18). Only ever shows values the backend actually
 * returned - never a fabricated benchmark or improvement figure (CLAUDE.md #33, #42). */
@Composable
fun RouteResultPanel(result: OptimizationResult, modifier: Modifier = Modifier) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                text = stringResource(R.string.result_title).uppercase(Locale.getDefault()),
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(24.dp),
            ) {
                ResultMetric(
                    label = stringResource(R.string.result_distance_label),
                    value = formatDistance(result.route.distanceMeters),
                )
                ResultMetric(
                    label = stringResource(R.string.result_duration_label),
                    value = formatDuration(result.route.durationSeconds),
                )
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(24.dp),
            ) {
                ResultMetric(label = stringResource(R.string.result_algorithm_label), value = result.algorithm)
                ResultMetric(
                    label = stringResource(R.string.result_status_label),
                    value = statusLabel(result),
                )
            }

            Text(
                text = result.explanation,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 4.dp),
            )
        }
    }
}

@Composable
private fun ResultMetric(label: String, value: String) {
    Column {
        Text(text = label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(text = value, style = MaterialTheme.typography.titleMedium)
    }
}

@Composable
private fun statusLabel(result: OptimizationResult): String =
    if (result.algorithm == "QPSO") {
        stringResource(R.string.status_optimized)
    } else {
        stringResource(R.string.status_direct_route)
    }

private fun formatDistance(meters: Double): String =
    if (meters >= 1000) String.format(Locale.getDefault(), "%.1f km", meters / 1000.0) else "${meters.roundToInt()} m"

private fun formatDuration(seconds: Double): String {
    val totalMinutes = (seconds / 60.0).roundToInt()
    val hours = totalMinutes / 60
    val minutes = totalMinutes % 60
    return if (hours > 0) "${hours} h ${minutes} min" else "$minutes min"
}
