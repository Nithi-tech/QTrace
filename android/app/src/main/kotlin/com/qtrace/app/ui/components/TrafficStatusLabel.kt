package com.qtrace.app.ui.components

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import com.qtrace.app.R
import com.qtrace.app.ui.screens.routeplanning.TrafficLayerStatus
import java.time.Duration
import java.time.Instant

/** "LIVE TRAFFIC / Updated 45 sec ago / Source: TomTom" (CLAUDE.md traffic master-prompt
 * #16) - built only from what the backend actually reported; never claims LIVE for a
 * loading/unavailable/stale result. */
@Composable
fun TrafficStatusLabel(
    status: TrafficLayerStatus,
    source: String?,
    updatedAt: String?,
    modifier: Modifier = Modifier,
) {
    val text = when (status) {
        TrafficLayerStatus.OFF -> return
        TrafficLayerStatus.LOADING -> stringResource(R.string.traffic_layer_loading)
        TrafficLayerStatus.UNAVAILABLE -> stringResource(R.string.traffic_layer_unavailable)
        TrafficLayerStatus.LIVE -> {
            val sourceLabel = sourceLabel(source)
            val ago = formatAgo(updatedAt)
            if (ago != null) {
                stringResource(R.string.traffic_layer_live_format, sourceLabel, ago)
            } else {
                stringResource(R.string.traffic_layer_live_just_now_format, sourceLabel)
            }
        }
    }
    Text(text = text, style = MaterialTheme.typography.labelSmall, modifier = modifier)
}

@Composable
private fun sourceLabel(source: String?): String = when (source) {
    "TOMTOM" -> stringResource(R.string.traffic_source_tomtom)
    else -> source.orEmpty()
}

@Composable
private fun formatAgo(updatedAt: String?): String? {
    val instant = updatedAt?.let { runCatching { Instant.parse(it) }.getOrNull() } ?: return null
    val seconds = Duration.between(instant, Instant.now()).seconds.coerceAtLeast(0)
    return if (seconds < 60) {
        stringResource(R.string.traffic_updated_seconds_ago, seconds.toInt())
    } else {
        stringResource(R.string.traffic_updated_minutes_ago, (seconds / 60).toInt())
    }
}
