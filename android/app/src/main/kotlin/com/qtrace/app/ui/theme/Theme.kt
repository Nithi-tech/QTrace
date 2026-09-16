package com.qtrace.app.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext

private val LightColors = lightColorScheme(
    primary = QTraceGreen40,
    onPrimary = QTraceNeutral99,
    primaryContainer = QTraceGreen90,
    onPrimaryContainer = QTraceGreen40,
    secondary = QTraceAmber40,
    onSecondary = QTraceNeutral99,
    background = QTraceNeutral99,
    onBackground = QTraceNeutral10,
    surface = QTraceNeutral99,
    onSurface = QTraceNeutral10,
    surfaceVariant = QTraceNeutral95,
    onSurfaceVariant = QTraceNeutral20,
    error = QTraceError40,
)

private val DarkColors = darkColorScheme(
    primary = QTraceGreen80,
    onPrimary = QTraceGreen40,
    primaryContainer = QTraceGreen40,
    onPrimaryContainer = QTraceGreen90,
    secondary = QTraceAmber80,
    onSecondary = QTraceAmber40,
    background = QTraceNeutral10,
    onBackground = QTraceNeutral90,
    surface = QTraceNeutral10,
    onSurface = QTraceNeutral90,
    surfaceVariant = QTraceNeutral20,
    onSurfaceVariant = QTraceNeutral90,
    error = QTraceError80,
)

@Composable
fun QTraceTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit,
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColors
        else -> LightColors
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = QTraceTypography,
        content = content,
    )
}
