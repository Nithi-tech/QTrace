package com.qtrace.app.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.qtrace.app.R
import com.qtrace.app.domain.model.QTraceError

/** User-facing error text (CLAUDE.md #21 - structured, never a raw exception message). */
@Composable
fun errorMessageFor(error: QTraceError): String = when (error) {
    QTraceError.NetworkUnavailable -> stringResource(R.string.error_network_unavailable)
    QTraceError.GeocodingFailed -> stringResource(R.string.error_geocoding_failed)
    QTraceError.RoutingProviderUnavailable -> stringResource(R.string.error_routing_unavailable)
    QTraceError.OptimizationInfeasible -> stringResource(R.string.error_optimization_infeasible)
    QTraceError.RequestTimedOut -> stringResource(R.string.error_routing_unavailable)
    QTraceError.SameLocation -> stringResource(R.string.error_same_location)
    QTraceError.InvalidLocation -> stringResource(R.string.error_invalid_location)
    is QTraceError.Unknown -> stringResource(R.string.error_generic_retry)
}

@Composable
fun ErrorBanner(
    error: QTraceError,
    onRetry: () -> Unit,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = errorMessageFor(error),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onErrorContainer,
                modifier = Modifier.weight(1f),
            )
            TextButton(onClick = onRetry) { Text(stringResource(R.string.retry_action)) }
            TextButton(onClick = onDismiss) { Text(stringResource(R.string.dismiss_action)) }
        }
    }
}

@Composable
fun OfflineBanner(modifier: Modifier = Modifier) {
    Card(
        modifier = modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.Center,
        ) {
            Text(
                text = stringResource(R.string.offline_banner),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}
