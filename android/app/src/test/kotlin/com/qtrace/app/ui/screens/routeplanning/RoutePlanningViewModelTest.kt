package com.qtrace.app.ui.screens.routeplanning

import com.qtrace.app.data.network.ConnectivityObserver
import com.qtrace.app.domain.model.Coordinate
import com.qtrace.app.domain.model.LocationSuggestion
import com.qtrace.app.domain.model.MapBounds
import com.qtrace.app.domain.model.OptimizationResult
import com.qtrace.app.domain.model.OptimizationStatus
import com.qtrace.app.domain.model.QTraceError
import com.qtrace.app.domain.model.QTraceResult
import com.qtrace.app.domain.model.RouteInfo
import com.qtrace.app.domain.model.TrafficAreaResult
import com.qtrace.app.domain.model.TrafficInfo
import com.qtrace.app.domain.repository.GeocodingRepository
import com.qtrace.app.domain.repository.RouteRepository
import com.qtrace.app.domain.repository.TrafficRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class RoutePlanningViewModelTest {

    private val testDispatcher = StandardTestDispatcher()

    private val start = LocationSuggestion("Start Point", Coordinate(12.97, 77.59))
    private val destination = LocationSuggestion("Destination Point", Coordinate(12.98, 77.60))

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    private fun viewModel(
        geocoding: GeocodingRepository = FakeGeocodingRepository(emptyMap()),
        route: RouteRepository = FakeRouteRepository(QTraceResult.Success(sampleOptimizationResult())),
        traffic: TrafficRepository = FakeTrafficRepository(),
        online: Boolean = true,
    ) = RoutePlanningViewModel(geocoding, route, traffic, FakeConnectivityObserver(online))

    @Test
    fun `typing a query returns suggestions after debounce`() = runTest(testDispatcher) {
        val geocoding = FakeGeocodingRepository(mapOf("mg road" to listOf(start)))
        val vm = viewModel(geocoding = geocoding)

        vm.onEvent(RoutePlanningEvent.StartQueryChanged("MG Road"))
        testDispatcher.scheduler.advanceTimeBy(400)
        testDispatcher.scheduler.runCurrent()

        assertEquals(listOf(start), vm.state.value.startSuggestions)
        assertEquals(false, vm.state.value.isSearchingStart)
    }

    @Test
    fun `query shorter than minimum length does not trigger a search`() = runTest(testDispatcher) {
        val geocoding = FakeGeocodingRepository(mapOf("m" to listOf(start)))
        val vm = viewModel(geocoding = geocoding)

        vm.onEvent(RoutePlanningEvent.StartQueryChanged("M"))
        testDispatcher.scheduler.advanceTimeBy(400)
        testDispatcher.scheduler.runCurrent()

        assertTrue(vm.state.value.startSuggestions.isEmpty())
    }

    @Test
    fun `selecting suggestions for both fields enables optimize`() = runTest(testDispatcher) {
        val vm = viewModel()

        vm.onEvent(RoutePlanningEvent.StartLocationSelected(start))
        vm.onEvent(RoutePlanningEvent.DestinationLocationSelected(destination))
        testDispatcher.scheduler.runCurrent()

        assertEquals(start, vm.state.value.startLocation)
        assertEquals(destination, vm.state.value.destinationLocation)
        assertTrue(vm.state.value.canOptimize)
    }

    @Test
    fun `optimize route success populates optimization result`() = runTest(testDispatcher) {
        val result = sampleOptimizationResult()
        val vm = viewModel(route = FakeRouteRepository(QTraceResult.Success(result)))

        vm.onEvent(RoutePlanningEvent.StartLocationSelected(start))
        vm.onEvent(RoutePlanningEvent.DestinationLocationSelected(destination))
        vm.onEvent(RoutePlanningEvent.OptimizeRouteClicked)
        testDispatcher.scheduler.advanceUntilIdle()

        assertEquals(result, vm.state.value.optimizationResult)
        assertNull(vm.state.value.error)
        assertEquals(false, vm.state.value.isPlanningRoute)
    }

    @Test
    fun `optimize route failure surfaces a structured error, not a crash`() = runTest(testDispatcher) {
        val vm = viewModel(route = FakeRouteRepository(QTraceResult.Failure(QTraceError.RoutingProviderUnavailable)))

        vm.onEvent(RoutePlanningEvent.StartLocationSelected(start))
        vm.onEvent(RoutePlanningEvent.DestinationLocationSelected(destination))
        vm.onEvent(RoutePlanningEvent.OptimizeRouteClicked)
        testDispatcher.scheduler.advanceUntilIdle()

        assertEquals(QTraceError.RoutingProviderUnavailable, vm.state.value.error)
        assertNull(vm.state.value.optimizationResult)
    }

    @Test
    fun `optimize route is a no-op when locations are missing`() = runTest(testDispatcher) {
        val route = FakeRouteRepository(QTraceResult.Success(sampleOptimizationResult()))
        val vm = viewModel(route = route)

        vm.onEvent(RoutePlanningEvent.OptimizeRouteClicked)
        testDispatcher.scheduler.advanceUntilIdle()

        assertEquals(0, route.callCount)
        assertNull(vm.state.value.optimizationResult)
    }

    @Test
    fun `going offline disables optimize`() = runTest(testDispatcher) {
        val vm = viewModel(online = false)

        vm.onEvent(RoutePlanningEvent.StartLocationSelected(start))
        vm.onEvent(RoutePlanningEvent.DestinationLocationSelected(destination))
        testDispatcher.scheduler.advanceUntilIdle()

        assertTrue(vm.state.value.isOffline)
        assertEquals(false, vm.state.value.canOptimize)
    }

    @Test
    fun `clearing start location resets its query and suggestions`() = runTest(testDispatcher) {
        val vm = viewModel()

        vm.onEvent(RoutePlanningEvent.StartLocationSelected(start))
        vm.onEvent(RoutePlanningEvent.ClearStartLocation)
        testDispatcher.scheduler.runCurrent()

        assertNull(vm.state.value.startLocation)
        assertEquals("", vm.state.value.startQuery)
    }

    @Test
    fun `traffic toggle off does not fetch even with bounds available`() = runTest(testDispatcher) {
        val traffic = FakeTrafficRepository()
        val vm = viewModel(traffic = traffic)

        vm.onEvent(RoutePlanningEvent.MapBoundsChanged(MapBounds(12.9, 77.5, 13.0, 77.6)))
        testDispatcher.scheduler.advanceUntilIdle()

        assertEquals(0, traffic.callCount)
        assertEquals(TrafficLayerStatus.OFF, vm.state.value.trafficLayerStatus)
    }

    @Test
    fun `enabling traffic with bounds already known fetches the area`() = runTest(testDispatcher) {
        val segments = TrafficAreaResult(
            enabled = true,
            available = true,
            source = "TOMTOM",
            updatedAt = "2026-01-01T00:00:00Z",
            segments = emptyList(),
        )
        val traffic = FakeTrafficRepository(QTraceResult.Success(segments))
        val vm = viewModel(traffic = traffic)

        vm.onEvent(RoutePlanningEvent.MapBoundsChanged(MapBounds(12.9, 77.5, 13.0, 77.6)))
        vm.onEvent(RoutePlanningEvent.TrafficToggled)
        testDispatcher.scheduler.advanceUntilIdle()

        assertEquals(1, traffic.callCount)
        assertEquals(TrafficLayerStatus.LIVE, vm.state.value.trafficLayerStatus)
        assertEquals("TOMTOM", vm.state.value.trafficSource)
    }

    @Test
    fun `unavailable traffic result is reported as unavailable not live`() = runTest(testDispatcher) {
        val unavailable = TrafficAreaResult(enabled = true, available = false, source = null, updatedAt = null, segments = emptyList())
        val traffic = FakeTrafficRepository(QTraceResult.Success(unavailable))
        val vm = viewModel(traffic = traffic)

        vm.onEvent(RoutePlanningEvent.MapBoundsChanged(MapBounds(12.9, 77.5, 13.0, 77.6)))
        vm.onEvent(RoutePlanningEvent.TrafficToggled)
        testDispatcher.scheduler.advanceUntilIdle()

        assertEquals(TrafficLayerStatus.UNAVAILABLE, vm.state.value.trafficLayerStatus)
    }

    @Test
    fun `traffic request failure does not raise the screen-wide error banner`() = runTest(testDispatcher) {
        val traffic = FakeTrafficRepository(QTraceResult.Failure(QTraceError.NetworkUnavailable))
        val vm = viewModel(traffic = traffic)

        vm.onEvent(RoutePlanningEvent.MapBoundsChanged(MapBounds(12.9, 77.5, 13.0, 77.6)))
        vm.onEvent(RoutePlanningEvent.TrafficToggled)
        testDispatcher.scheduler.advanceUntilIdle()

        assertEquals(TrafficLayerStatus.UNAVAILABLE, vm.state.value.trafficLayerStatus)
        assertNull(vm.state.value.error)
    }

    @Test
    fun `toggling traffic off clears segments and stops future fetches`() = runTest(testDispatcher) {
        val traffic = FakeTrafficRepository()
        val vm = viewModel(traffic = traffic)

        vm.onEvent(RoutePlanningEvent.MapBoundsChanged(MapBounds(12.9, 77.5, 13.0, 77.6)))
        vm.onEvent(RoutePlanningEvent.TrafficToggled)
        testDispatcher.scheduler.advanceUntilIdle()
        vm.onEvent(RoutePlanningEvent.TrafficToggled)
        testDispatcher.scheduler.advanceUntilIdle()
        val callsAfterDisable = traffic.callCount

        vm.onEvent(RoutePlanningEvent.MapBoundsChanged(MapBounds(20.0, 77.5, 21.0, 78.6)))
        testDispatcher.scheduler.advanceUntilIdle()

        assertEquals(TrafficLayerStatus.OFF, vm.state.value.trafficLayerStatus)
        assertTrue(vm.state.value.trafficSegments.isEmpty())
        assertEquals(callsAfterDisable, traffic.callCount)
    }

    @Test
    fun `a small camera pan does not trigger a redundant traffic fetch`() = runTest(testDispatcher) {
        val traffic = FakeTrafficRepository()
        val vm = viewModel(traffic = traffic)

        vm.onEvent(RoutePlanningEvent.MapBoundsChanged(MapBounds(12.90, 77.50, 13.00, 77.60)))
        vm.onEvent(RoutePlanningEvent.TrafficToggled)
        testDispatcher.scheduler.advanceUntilIdle()
        val firstCallCount = traffic.callCount

        // Shifted by ~1% of the viewport span - not significant.
        vm.onEvent(RoutePlanningEvent.MapBoundsChanged(MapBounds(12.901, 77.501, 13.001, 77.601)))
        testDispatcher.scheduler.advanceUntilIdle()

        assertEquals(firstCallCount, traffic.callCount)
    }

    private fun sampleOptimizationResult() = OptimizationResult(
        route = RouteInfo(distanceMeters = 1500.0, durationSeconds = 240.0, geometry = emptyList()),
        algorithm = "DIRECT_ROUTE",
        status = OptimizationStatus.COMPLETED,
        stopsCount = 2,
        objectiveValue = null,
        optimizationRuntimeMs = 5.0,
        explanation = "Single origin-to-destination request",
        traffic = TrafficInfo(
            enabled = true,
            available = false,
            status = "UNAVAILABLE",
            source = null,
            confidence = null,
            level = null,
        ),
        trafficImpactSeconds = null,
    )
}

private class FakeGeocodingRepository(
    private val resultsByQuery: Map<String, List<LocationSuggestion>>,
) : GeocodingRepository {
    override suspend fun search(query: String): QTraceResult<List<LocationSuggestion>> =
        QTraceResult.Success(resultsByQuery[query.lowercase()].orEmpty())
}

private class FakeRouteRepository(
    private val result: QTraceResult<OptimizationResult>,
) : RouteRepository {
    var callCount = 0
        private set

    override suspend fun planRoute(origin: Coordinate, destination: Coordinate): QTraceResult<OptimizationResult> {
        callCount++
        return result
    }
}

private class FakeConnectivityObserver(private val online: Boolean) : ConnectivityObserver {
    override fun isOnline(): Flow<Boolean> = flowOf(online)
}

private class FakeTrafficRepository(
    private val result: QTraceResult<TrafficAreaResult> = QTraceResult.Success(
        TrafficAreaResult(enabled = true, available = false, source = null, updatedAt = null, segments = emptyList()),
    ),
) : TrafficRepository {
    var callCount = 0
        private set
    var lastBounds: MapBounds? = null
        private set

    override suspend fun getTrafficArea(bounds: MapBounds): QTraceResult<TrafficAreaResult> {
        callCount++
        lastBounds = bounds
        return result
    }
}
