import pytest

from app.schemas.routing import Coordinate
from app.schemas.traffic import TrafficFlowSegment
from app.traffic.area_sampler import TrafficAreaSampler, build_sample_grid
from app.traffic.cache import TTLCache
from app.traffic.exceptions import TrafficProviderUnavailableError


def _long_flow(num_points: int) -> TrafficFlowSegment:
    coordinates = [[77.0 + i * 0.001, 13.0 + i * 0.001] for i in range(num_points)]
    return TrafficFlowSegment(
        geometry={"type": "LineString", "coordinates": coordinates},
        current_speed_mps=10.0,
        free_flow_speed_mps=15.0,
        confidence=0.9,
    )


def test_build_sample_grid_never_exceeds_max_points():
    points = build_sample_grid(west=77.0, south=13.0, east=77.2, north=13.2, max_points=9)
    assert 0 < len(points) <= 9


def test_build_sample_grid_points_are_inside_bbox():
    points = build_sample_grid(west=77.0, south=13.0, east=77.2, north=13.2, max_points=16)
    for point in points:
        assert 77.0 <= point.longitude <= 77.2
        assert 13.0 <= point.latitude <= 13.2


def test_build_sample_grid_rejects_degenerate_bbox():
    assert build_sample_grid(west=77.0, south=13.0, east=77.0, north=13.2, max_points=9) == []
    assert build_sample_grid(west=77.0, south=13.0, east=77.2, north=13.0, max_points=9) == []


class FakeTomTomProvider:
    def __init__(self, flows: dict[tuple[float, float], TrafficFlowSegment | None], fail: bool = False):
        self._flows = flows
        self._fail = fail
        self.calls = 0

    async def get_flow_at_point(self, coordinate: Coordinate) -> TrafficFlowSegment | None:
        self.calls += 1
        if self._fail:
            raise TrafficProviderUnavailableError("boom")
        return self._flows.get((round(coordinate.latitude, 4), round(coordinate.longitude, 4)))


def _flow(lon_a: float, lat_a: float, lon_b: float, lat_b: float, speed: float = 10.0) -> TrafficFlowSegment:
    return TrafficFlowSegment(
        geometry={"type": "LineString", "coordinates": [[lon_a, lat_a], [lon_b, lat_b]]},
        current_speed_mps=speed,
        free_flow_speed_mps=15.0,
        confidence=0.9,
    )


@pytest.mark.asyncio
async def test_no_provider_returns_empty():
    sampler = TrafficAreaSampler(tomtom_provider=None, cache=TTLCache(ttl_seconds=60), max_points=9)
    result = await sampler.sample(west=77.0, south=13.0, east=77.2, north=13.2)
    assert result == []


@pytest.mark.asyncio
async def test_provider_failure_is_treated_as_no_data_not_a_crash():
    provider = FakeTomTomProvider(flows={}, fail=True)
    sampler = TrafficAreaSampler(tomtom_provider=provider, cache=TTLCache(ttl_seconds=60), max_points=4)
    result = await sampler.sample(west=77.0, south=13.0, east=77.2, north=13.2)
    assert result == []


@pytest.mark.asyncio
async def test_identical_geometry_from_different_sample_points_is_deduped():
    same_segment = _flow(77.05, 13.05, 77.06, 13.06)
    points = build_sample_grid(west=77.0, south=13.0, east=77.2, north=13.2, max_points=4)
    flows = {(round(p.latitude, 4), round(p.longitude, 4)): same_segment for p in points}
    provider = FakeTomTomProvider(flows=flows)
    sampler = TrafficAreaSampler(tomtom_provider=provider, cache=TTLCache(ttl_seconds=60), max_points=4)

    result = await sampler.sample(west=77.0, south=13.0, east=77.2, north=13.2)

    assert len(result) == 1


@pytest.mark.asyncio
async def test_distinct_geometries_are_all_kept():
    points = build_sample_grid(west=77.0, south=13.0, east=77.2, north=13.2, max_points=4)
    flows = {
        (round(p.latitude, 4), round(p.longitude, 4)): _flow(
            p.longitude, p.latitude, p.longitude + 0.001, p.latitude + 0.001
        )
        for p in points
    }
    provider = FakeTomTomProvider(flows=flows)
    sampler = TrafficAreaSampler(tomtom_provider=provider, cache=TTLCache(ttl_seconds=60), max_points=4)

    result = await sampler.sample(west=77.0, south=13.0, east=77.2, north=13.2)

    assert len(result) == len(points)


@pytest.mark.asyncio
async def test_long_geometry_is_decimated_but_keeps_endpoints():
    provider = FakeTomTomProvider(flows={(13.05, 80.25): _long_flow(1000)})
    sampler = TrafficAreaSampler(tomtom_provider=provider, cache=TTLCache(ttl_seconds=60), max_points=1)

    result = await sampler.sample(west=80.2, south=13.0, east=80.3, north=13.1)

    assert len(result) == 1
    coordinates = result[0].geometry["coordinates"]
    assert len(coordinates) <= 80
    original = _long_flow(1000).geometry["coordinates"]
    assert coordinates[0] == original[0]
    assert coordinates[-1] == original[-1]


@pytest.mark.asyncio
async def test_repeated_sample_within_ttl_reuses_cache_not_a_new_call():
    # Uses real (non-None) flow results: a None result isn't distinguishable from "not
    # cached yet" in TTLCache.get() (the same limitation already accepted in
    # traffic_service.py's identical cache-lookup pattern) - caching still works for
    # every point TomTom actually has data for, which is the case this matters for.
    points = build_sample_grid(west=77.0, south=13.0, east=77.2, north=13.2, max_points=4)
    flows = {
        (round(p.latitude, 4), round(p.longitude, 4)): _flow(
            p.longitude, p.latitude, p.longitude + 0.001, p.latitude + 0.001
        )
        for p in points
    }
    provider = FakeTomTomProvider(flows=flows)
    cache = TTLCache(ttl_seconds=60)
    sampler = TrafficAreaSampler(tomtom_provider=provider, cache=cache, max_points=4)

    await sampler.sample(west=77.0, south=13.0, east=77.2, north=13.2)
    first_call_count = provider.calls
    await sampler.sample(west=77.0, south=13.0, east=77.2, north=13.2)

    assert provider.calls == first_call_count
