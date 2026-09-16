import httpx
import pytest
import respx

from app.routing.exceptions import (
    InvalidRouteInputError,
    RoutingProviderTimeoutError,
    RoutingProviderUnavailableError,
)
from app.routing.osrm_provider import OSRMProvider
from app.schemas.routing import Coordinate

BASE_URL = "http://osrm.test"


@pytest.mark.asyncio
@respx.mock
async def test_route_converts_lat_lon_and_parses_result():
    route = respx.get(f"{BASE_URL}/route/v1/driving/77.59,12.97;77.6,12.98").mock(
        return_value=httpx.Response(
            200,
            json={
                "code": "Ok",
                "routes": [
                    {
                        "distance": 1500.0,
                        "duration": 240.0,
                        "geometry": {"type": "LineString", "coordinates": [[77.59, 12.97], [77.6, 12.98]]},
                    }
                ],
            },
        )
    )

    provider = OSRMProvider(base_url=BASE_URL)
    result = await provider.route(
        [Coordinate(latitude=12.97, longitude=77.59), Coordinate(latitude=12.98, longitude=77.6)]
    )

    assert route.called
    assert result.distance_meters == 1500.0
    assert result.duration_seconds == 240.0


@pytest.mark.asyncio
@respx.mock
async def test_matrix_returns_full_pairwise_matrix():
    respx.get(f"{BASE_URL}/table/v1/driving/77.59,12.97;77.6,12.98").mock(
        return_value=httpx.Response(
            200,
            json={
                "code": "Ok",
                "distances": [[0, 1500], [1500, 0]],
                "durations": [[0, 240], [240, 0]],
            },
        )
    )

    provider = OSRMProvider(base_url=BASE_URL)
    result = await provider.matrix(
        [Coordinate(latitude=12.97, longitude=77.59), Coordinate(latitude=12.98, longitude=77.6)]
    )

    assert result.distances_meters == [[0, 1500], [1500, 0]]
    assert result.durations_seconds == [[0, 240], [240, 0]]


@pytest.mark.asyncio
async def test_route_rejects_single_coordinate():
    provider = OSRMProvider(base_url=BASE_URL)
    with pytest.raises(InvalidRouteInputError):
        await provider.route([Coordinate(latitude=12.97, longitude=77.59)])


@pytest.mark.asyncio
@respx.mock
async def test_route_raises_unavailable_on_no_route_found():
    respx.get(f"{BASE_URL}/route/v1/driving/77.59,12.97;77.6,12.98").mock(
        return_value=httpx.Response(200, json={"code": "NoRoute", "routes": []})
    )

    provider = OSRMProvider(base_url=BASE_URL)
    with pytest.raises(RoutingProviderUnavailableError):
        await provider.route(
            [Coordinate(latitude=12.97, longitude=77.59), Coordinate(latitude=12.98, longitude=77.6)]
        )


@pytest.mark.asyncio
@respx.mock
async def test_route_raises_timeout_after_retries_exhausted():
    respx.get(f"{BASE_URL}/route/v1/driving/77.59,12.97;77.6,12.98").mock(
        side_effect=httpx.TimeoutException("timed out")
    )

    provider = OSRMProvider(base_url=BASE_URL, max_retries=1)
    with pytest.raises(RoutingProviderTimeoutError):
        await provider.route(
            [Coordinate(latitude=12.97, longitude=77.59), Coordinate(latitude=12.98, longitude=77.6)]
        )


@pytest.mark.asyncio
async def test_geocode_is_not_supported():
    provider = OSRMProvider(base_url=BASE_URL)
    with pytest.raises(NotImplementedError):
        await provider.geocode("123 Main St")


@pytest.mark.asyncio
@respx.mock
async def test_route_uses_configured_profile_in_url():
    route = respx.get(f"{BASE_URL}/route/v1/bicycle/77.59,12.97;77.6,12.98").mock(
        return_value=httpx.Response(
            200,
            json={"code": "Ok", "routes": [{"distance": 1200.0, "duration": 300.0, "geometry": None}]},
        )
    )

    provider = OSRMProvider(base_url=BASE_URL, profile="bicycle")
    await provider.route(
        [Coordinate(latitude=12.97, longitude=77.59), Coordinate(latitude=12.98, longitude=77.6)]
    )

    assert route.called
