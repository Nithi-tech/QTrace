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
import com.qtrace.app.domain.model.TrafficInfo
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
                    value = formatDuration(effectiveDurationSeconds(result)),
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

            if (result.traffic.enabled) {
                ResultMetric(
                    label = stringResource(R.string.result_traffic_label),
                    value = trafficValueLabel(result.traffic),
                )
                freeFlowLabel(result)?.let { freeFlow ->
                    Text(
                        text = freeFlow,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
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

/** Shows QTrace's own congestion classification for this route (backend
 * app/traffic/aggregation.py::classify_traffic_level) - never a raw freshness/source label,
 * and never a guess when traffic is unavailable (CLAUDE.md #12, #43). */
@Composable
private fun trafficValueLabel(traffic: TrafficInfo): String {
    if (!traffic.available) return stringResource(R.string.traffic_status_unavailable)
    return when (traffic.level) {
        "LOW" -> stringResource(R.string.traffic_level_low)
        "MODERATE" -> stringResource(R.string.traffic_level_medium)
        "HEAVY" -> stringResource(R.string.traffic_level_high)
        // traffic.available is true here, so this is never "no traffic data" - only an
        // older backend not yet sending `level`. Must not reuse the unavailable string,
        // which would contradict the free-flow line shown alongside it.
        else -> stringResource(R.string.traffic_level_unknown)
    }
}

/** "Estimated time" already includes [OptimizationResult.trafficImpactSeconds] (below) so the
 * headline is the number a driver should actually plan around, not an optimistic free-flow
 * figure (CLAUDE.md #71/#72 - route results should expose useful, honest metadata). */
private fun effectiveDurationSeconds(result: OptimizationResult): Double =
    result.route.durationSeconds + (result.trafficImpactSeconds ?: 0.0)

@Composable
private fun freeFlowLabel(result: OptimizationResult): String? {
    val impact = result.trafficImpactSeconds
    if (impact == null || impact < 30.0) return null
    return stringResource(R.string.traffic_free_flow_format, formatDuration(result.route.durationSeconds))
}

private fun formatDistance(meters: Double): String =
    if (meters >= 1000) String.format(Locale.getDefault(), "%.1f km", meters / 1000.0) else "${meters.roundToInt()} m"

private fun formatDuration(seconds: Double): String {
    val totalMinutes = (seconds / 60.0).roundToInt()
    val hours = totalMinutes / 60
    val minutes = totalMinutes % 60
    return if (hours > 0) "${hours} h ${minutes} min" else "$minutes min"
}
