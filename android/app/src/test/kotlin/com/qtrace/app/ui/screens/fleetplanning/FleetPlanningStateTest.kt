package com.qtrace.app.ui.screens.fleetplanning

import com.qtrace.app.domain.model.Coordinate
import com.qtrace.app.domain.model.LocationSuggestion
import com.qtrace.app.domain.model.ScenarioType
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class FleetPlanningStateTest {

    private val depot = LocationSuggestion(label = "Depot", coordinate = Coordinate(13.08, 80.27))
    private val validVehicle = VehicleSpecInput(vehicleType = "Van", count = "1", capacity = "100")
    private val validDestination = DestinationInput(name = "T Nagar", address = "T Nagar")

    @Test
    fun `cannot generate routes without a depot`() {
        val state = FleetPlanningState(vehicles = listOf(validVehicle), destinations = listOf(validDestination))

        assertFalse(state.canGenerateRoutes)
    }

    @Test
    fun `cannot generate routes with an invalid vehicle`() {
        val invalidVehicle = validVehicle.copy(capacity = "0")
        val state = FleetPlanningState(depot = depot, vehicles = listOf(invalidVehicle), destinations = listOf(validDestination))

        assertFalse(state.canGenerateRoutes)
        assertFalse(state.canProceedFromFleet)
    }

    @Test
    fun `cannot generate routes with an invalid destination`() {
        val invalidDestination = DestinationInput(name = "", address = null, coordinate = null)
        val state = FleetPlanningState(depot = depot, vehicles = listOf(validVehicle), destinations = listOf(invalidDestination))

        assertFalse(state.canGenerateRoutes)
        assertFalse(state.canProceedFromDestinations)
    }

    @Test
    fun `can generate routes once depot, a valid vehicle, and a valid destination all exist`() {
        val state = FleetPlanningState(depot = depot, vehicles = listOf(validVehicle), destinations = listOf(validDestination))

        assertTrue(state.canGenerateRoutes)
    }

    @Test
    fun `cannot generate routes while offline`() {
        val state = FleetPlanningState(
            depot = depot,
            vehicles = listOf(validVehicle),
            destinations = listOf(validDestination),
            isOffline = true,
        )

        assertFalse(state.canGenerateRoutes)
    }

    @Test
    fun `destination with a confirmed coordinate is valid without an address`() {
        val destination = DestinationInput(name = "Depot Stop", coordinate = Coordinate(13.05, 80.24))

        assertTrue(destination.isValid)
        assertTrue(destination.isConfirmed)
    }

    @Test
    fun `destination with neither a coordinate nor an address is invalid and unconfirmed`() {
        val destination = DestinationInput(name = "Bad Row", coordinate = null, address = null)

        assertFalse(destination.isValid)
        assertFalse(destination.isConfirmed)
    }

    @Test
    fun `destination with only a typed query and no confirmed selection is invalid`() {
        val destination = DestinationInput(query = "T Nagar")

        assertFalse(destination.isValid)
        assertFalse(destination.isConfirmed)
    }

    @Test
    fun `scenario step only proceeds once a scenario is chosen`() {
        val state = FleetPlanningState()
        assertFalse(state.canProceedFromScenario)

        assertTrue(state.copy(scenario = ScenarioType.GOODS_LOGISTICS).canProceedFromScenario)
    }
}
