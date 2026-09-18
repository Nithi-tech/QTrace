from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx

from app.routing.osrm_provider import OSRMProvider
from app.schemas.map_matching import TimedCoordinate
from app.schemas.routing import Coordinate

BASE_URL = "http://osrm.test"

# Shapes below mirror real responses verified live against router.project-osrm.org
# during development (docs/TRAFFIC_ARCHITECTURE.md).
_MATCH_RESPONSE = {
    "code": "Ok",
    "matchings": [
        {
            "geometry": {"type": "LineString", "coordinates": [[77.5946, 12.9716], [77.6008, 12.9766]]},
            "legs": [
                {
                    "distance": 1026.3,
                    "duration": 92.1,
                    "annotation": {
                        "nodes": [11506245560, 10595455530, 5340711536],
                        "distance": [500.0, 526.3],
                        "duration": [45.0, 47.1],
                        "speed": [11.1, 11.2],
                    },
                }
            ],
        }
    ],
    "tracepoints": [
        {"matchings_index": 0, "waypoint_index": 0},
        {"matchings_index": 0, "waypoint_index": 1},
    ],
}

_NEAREST_RESPONSE = {
    "code": "Ok",
    "waypoints": [
        {
            "nodes": [11506245560, 10595455530],
            "location": [77.594697, 12.971848],
            "name": "Vittal Mallya Road",
            "distance": 29.38,
        }
    ],
}


@pytest.mark.asyncio
@respx.mock
async def test_match_trace_extracts_edges_and_observed_speed_from_real_timestamps():
    respx.get(f"{BASE_URL}/match/v1/driving/77.5946,12.9716;77.6008,12.9766").mock(
        return_value=httpx.Response(200, json=_MATCH_RESPONSE)
    )

    t0 = datetime(2026, 9, 17, 8, 0, 0, tzinfo=timezone.utc)
    points = [
        TimedCoordinate(latitude=12.9716, longitude=77.5946, timestamp=t0),
        TimedCoordinate(latitude=12.9766, longitude=77.6008, timestamp=t0 + timedelta(seconds=60)),
    ]

    provider = OSRMProvider(base_url=BASE_URL)
    result = await provider.match_trace(points)

    assert result.matched is True
    assert len(result.legs) == 1
    leg = result.legs[0]
    assert leg.distance_meters == 1026.3
    assert leg.observed_duration_seconds == 60.0
    assert leg.observed_speed_mps == pytest.approx(1026.3 / 60.0)
    assert len(leg.edges) == 2
    assert leg.edges[0].node_a == 11506245560
    assert leg.edges[0].segment_key == "10595455530:11506245560"


@pytest.mark.asyncio
@respx.mock
async def test_match_trace_reports_not_matched_on_no_match_code():
    respx.get(f"{BASE_URL}/match/v1/driving/77.5946,12.9716;77.6008,12.9766").mock(
        return_value=httpx.Response(200, json={"code": "NoMatch"})
    )

    t0 = datetime(2026, 9, 17, 8, 0, 0, tzinfo=timezone.utc)
    points = [
        TimedCoordinate(latitude=12.9716, longitude=77.5946, timestamp=t0),
        TimedCoordinate(latitude=12.9766, longitude=77.6008, timestamp=t0 + timedelta(seconds=60)),
    ]

    provider = OSRMProvider(base_url=BASE_URL)
    result = await provider.match_trace(points)

    assert result.matched is False


@pytest.mark.asyncio
@respx.mock
async def test_snap_point_extracts_node_pair():
    respx.get(f"{BASE_URL}/nearest/v1/driving/77.5946,12.9716").mock(
        return_value=httpx.Response(200, json=_NEAREST_RESPONSE)
    )

    provider = OSRMProvider(base_url=BASE_URL)
    result = await provider.snap_point(Coordinate(latitude=12.9716, longitude=77.5946))

    assert result.matched is True
    assert result.edge.node_a == 11506245560
    assert result.edge.node_b == 10595455530


@pytest.mark.asyncio
async def test_match_trace_with_no_points_is_not_matched():
    provider = OSRMProvider(base_url=BASE_URL)
    result = await provider.match_trace([])
    assert result.matched is False
