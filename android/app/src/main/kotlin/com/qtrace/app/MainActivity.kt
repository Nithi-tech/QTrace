package com.qtrace.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.qtrace.app.ui.navigation.QTraceNavHost
import com.qtrace.app.ui.theme.QTraceTheme
import dagger.hilt.android.AndroidEntryPoint
import org.maplibre.android.MapLibre

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        MapLibre.getInstance(applicationContext)
        enableEdgeToEdge()

        setContent {
            QTraceTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    QTraceNavHost()
                }
            }
        }
    }
}
