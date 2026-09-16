package com.qtrace.app.ui.screens.routeplanning

import com.qtrace.app.domain.model.Coordinate
import com.qtrace.app.domain.model.LocationSuggestion
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class RoutePlanningStateTest {

    private val start = LocationSuggestion("Start", Coordinate(12.97, 77.59))
    private val destination = LocationSuggestion("Destination", Coordinate(12.98, 77.60))

    @Test
    fun `cannot optimize without both locations`() {
        assertFalse(RoutePlanningState().canOptimize)
        assertFalse(RoutePlanningState(startLocation = start).canOptimize)
        assertFalse(RoutePlanningState(destinationLocation = destination).canOptimize)
    }

    @Test
    fun `can optimize once both distinct locations are selected`() {
        val state = RoutePlanningState(startLocation = start, destinationLocation = destination)
        assertTrue(state.canOptimize)
    }

    @Test
    fun `cannot optimize when start and destination share the same coordinate`() {
        val sameSpotDestination = LocationSuggestion("Same spot, different name", start.coordinate)
        val state = RoutePlanningState(startLocation = start, destinationLocation = sameSpotDestination)

        assertTrue(state.isSameLocationSelected)
        assertFalse(state.canOptimize)
    }

    @Test
    fun `cannot optimize while a request is already in flight`() {
        val state = RoutePlanningState(startLocation = start, destinationLocation = destination, isPlanningRoute = true)
        assertFalse(state.canOptimize)
    }

    @Test
    fun `cannot optimize while offline`() {
        val state = RoutePlanningState(startLocation = start, destinationLocation = destination, isOffline = true)
        assertFalse(state.canOptimize)
    }
}
