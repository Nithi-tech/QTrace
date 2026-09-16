package com.qtrace.app.ui.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.qtrace.app.ui.screens.routeplanning.RoutePlanningScreen

/** Single destination today; a real NavHost is set up now so adding a second screen (e.g. a
 * multi-stop VRP planner, CLAUDE.md #15) later doesn't require restructuring navigation. */
@Composable
fun QTraceNavHost(navController: NavHostController = rememberNavController()) {
    NavHost(navController = navController, startDestination = Destinations.ROUTE_PLANNING) {
        composable(Destinations.ROUTE_PLANNING) {
            RoutePlanningScreen()
        }
    }
}
