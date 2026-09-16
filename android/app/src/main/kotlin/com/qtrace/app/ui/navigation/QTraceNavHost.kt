package com.qtrace.app.ui.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.qtrace.app.ui.screens.fleetplanning.FleetPlanningScreen
import com.qtrace.app.ui.screens.routeplanning.RoutePlanningScreen

/** Single-vehicle route planning stays the start destination and default app behavior
 * unchanged; multi-vehicle fleet planning (CLAUDE.md #15) is reached from its header action. */
@Composable
fun QTraceNavHost(navController: NavHostController = rememberNavController()) {
    NavHost(navController = navController, startDestination = Destinations.ROUTE_PLANNING) {
        composable(Destinations.ROUTE_PLANNING) {
            RoutePlanningScreen(onNavigateToFleetPlanning = { navController.navigate(Destinations.FLEET_PLANNING) })
        }
        composable(Destinations.FLEET_PLANNING) {
            FleetPlanningScreen(onExit = { navController.popBackStack() })
        }
    }
}
