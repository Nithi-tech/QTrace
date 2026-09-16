package com.qtrace.app.ui.components

import androidx.compose.foundation.layout.size
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import com.qtrace.app.R
import com.qtrace.app.domain.model.LocationSuggestion

/**
 * Address/place search field with a suggestions dropdown (CLAUDE.md spec #9/#10). Map-tap
 * selection is intentionally not implemented in this first version (spec #11 - documented as a
 * future enhancement rather than added speculatively now).
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LocationSearchField(
    label: String,
    query: String,
    suggestions: List<LocationSuggestion>,
    isExpanded: Boolean,
    isSearching: Boolean,
    onQueryChanged: (String) -> Unit,
    onFocused: () -> Unit,
    onDismiss: () -> Unit,
    onSuggestionSelected: (LocationSuggestion) -> Unit,
    onClear: () -> Unit,
    placeholder: String,
    modifier: Modifier = Modifier,
) {
    var expandedState by remember(isExpanded, suggestions) {
        mutableStateOf(isExpanded && suggestions.isNotEmpty())
    }

    ExposedDropdownMenuBox(
        expanded = expandedState,
        onExpandedChange = { expanded ->
            if (expanded) onFocused() else onDismiss()
            expandedState = expanded
        },
        modifier = modifier,
    ) {
        OutlinedTextField(
            value = query,
            onValueChange = onQueryChanged,
            label = { Text(label) },
            placeholder = { Text(placeholder) },
            singleLine = true,
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
            trailingIcon = {
                when {
                    isSearching -> CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        strokeWidth = 2.dp,
                    )
                    query.isNotEmpty() -> IconButton(onClick = onClear) {
                        Icon(
                            Icons.Filled.Clear,
                            contentDescription = stringResource(R.string.content_description_clear_field),
                        )
                    }
                }
            },
            modifier = Modifier
                .menuAnchor()
                .semantics { contentDescription = label },
        )

        if (suggestions.isNotEmpty()) {
            ExposedDropdownMenu(
                expanded = expandedState,
                onDismissRequest = onDismiss,
            ) {
                suggestions.forEach { suggestion ->
                    DropdownMenuItem(
                        text = { Text(suggestion.label, style = MaterialTheme.typography.bodyMedium) },
                        onClick = {
                            onSuggestionSelected(suggestion)
                            expandedState = false
                        },
                        leadingIcon = { Icon(Icons.Filled.LocationOn, contentDescription = null) },
                    )
                }
            }
        }
    }
}
