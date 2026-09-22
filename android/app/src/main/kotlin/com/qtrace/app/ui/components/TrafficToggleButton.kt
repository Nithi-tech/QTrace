package com.qtrace.app.ui.components

import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.qtrace.app.R

/** Google-Maps-style floating Traffic ON/OFF control (CLAUDE.md traffic master-prompt #14/#36).
 * A Material 3 FilterChip - the same selection control already used elsewhere in this app
 * (fleet objective selection), not a bespoke toggle widget. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TrafficToggleButton(enabled: Boolean, onToggle: () -> Unit, modifier: Modifier = Modifier) {
    FilterChip(
        selected = enabled,
        onClick = onToggle,
        label = { Text(stringResource(R.string.traffic_toggle_label)) },
        leadingIcon = { Icon(Icons.Filled.Warning, contentDescription = null, modifier = Modifier.size(18.dp)) },
        colors = FilterChipDefaults.filterChipColors(selectedContainerColor = Color(0xFFEF6C00).copy(alpha = 0.22f)),
        modifier = modifier,
    )
}
