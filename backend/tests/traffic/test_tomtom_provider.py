import httpx
import pytest
import respx

from app.schemas.routing import Coordinate
from app.traffic.exceptions import (
    TrafficConfigurationError,
    TrafficProviderTimeoutError,
    TrafficProviderUnavailableError,
)
from app.traffic.tomtom_provider import TomTomTrafficProvider

FLOW_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
INCIDENTS_URL = "https://api.tomtom.com/traffic/services/5/incidentDetails"

# Shape verified live against the real TomTom API during development
# (docs/TRAFFIC_ARCHITECTURE.md) - currentSpeed/freeFlowSpeed are km/h.
_REAL_FLOW_RESPONSE = {
    "flowSegmentData": {
        "frc": "FRC2",
        "currentSpeed": 19,
        "freeFlowSpeed": 23,
        "currentTravelTime": 491,
        "freeFlowTravelTime": 406,
        "confidence": 0.953528,
        "roadClosure": False,
        "coordinates": {
            "coordinate": [
                {"latitude": 13.080843740241827, "longitude": 80.27090904774866},
                {"latitude": 13.080885297069777, "longitude": 80.27090904774866},
            ]
        },
    }
}

# Shape verified live against the real TomTom Incidents API.
_REAL_INCIDENTS_RESPONSE = {
    "incidents": [
        {
            "type": "Feature",
            "properties": {
                "iconCategory": 8,
                "magnitudeOfDelay": 4,
                "events": [{"description": "Closed"}],
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [[80.2017912036, 12.9524450521], [80.2015913791, 12.9524571417]],
            },
        },
        {
            "type": "Feature",
            "properties": {"iconCategory": 1, "magnitudeOfDelay": 1, "events": [{"description": "Accident"}]},
            "geometry": {"type": "LineString", "coordinates": [[80.21, 12.96], [80.211, 12.961]]},
        },
    ]
}


@pytest.mark.asyncio
async def test_get_flow_without_api_key_raises_configuration_error():
    provider = TomTomTrafficProvider(api_key=None)
    with pytest.raises(TrafficConfigurationError):
        await provider.get_flow_at_point(Coordinate(latitude=13.08, longitude=80.27))


@pytest.mark.asyncio
@respx.mock
async def test_get_flow_parses_real_response_shape_and_converts_kmph_to_mps():
    route = respx.get(FLOW_URL).mock(return_value=httpx.Response(200, json=_REAL_FLOW_RESPONSE))

    provider = TomTomTrafficProvider(api_key="test-key")
    result = await provider.get_flow_at_point(Coordinate(latitude=13.0827, longitude=80.2707))

    assert route.called
    assert result is not None
    assert result.current_speed_mps == pytest.approx(19 / 3.6)
    assert result.free_flow_speed_mps == pytest.approx(23 / 3.6)
    assert result.confidence == 0.953528
    assert result.geometry["coordinates"][0] == [80.27090904774866, 13.080843740241827]


@pytest.mark.asyncio
@respx.mock
async def test_get_flow_returns_none_when_speed_fields_missing():
    respx.get(FLOW_URL).mock(return_value=httpx.Response(200, json={"flowSegmentData": {"frc": "FRC2"}}))

    provider = TomTomTrafficProvider(api_key="test-key")
    result = await provider.get_flow_at_point(Coordinate(latitude=13.08, longitude=80.27))

    assert result is None


@pytest.mark.asyncio
@respx.mock
async def test_get_flow_raises_unavailable_on_auth_failure_without_retry():
    route = respx.get(FLOW_URL).mock(return_value=httpx.Response(401))

    provider = TomTomTrafficProvider(api_key="bad-key", max_retries=3)
    with pytest.raises(TrafficProviderUnavailableError):
        await provider.get_flow_at_point(Coordinate(latitude=13.08, longitude=80.27))

    assert route.call_count == 1  # never retried an auth failure


@pytest.mark.asyncio
@respx.mock
async def test_get_flow_raises_timeout_after_retries_exhausted():
    respx.get(FLOW_URL).mock(side_effect=httpx.TimeoutException("timed out"))

    provider = TomTomTrafficProvider(api_key="test-key", max_retries=1)
    with pytest.raises(TrafficProviderTimeoutError):
        await provider.get_flow_at_point(Coordinate(latitude=13.08, longitude=80.27))


@pytest.mark.asyncio
@respx.mock
async def test_get_incidents_parses_closure_and_regular_incident():
    respx.get(INCIDENTS_URL).mock(return_value=httpx.Response(200, json=_REAL_INCIDENTS_RESPONSE))

    provider = TomTomTrafficProvider(api_key="test-key")
    incidents = await provider.get_incidents(80.0, 12.9, 80.3, 13.0)

    assert len(incidents) == 2
    assert incidents[0].road_closed is True
    assert incidents[0].severity == 10.0  # magnitude 4 * 2.5
    assert incidents[0].incident_type == "Closed"
    assert incidents[1].road_closed is False
    assert incidents[1].severity == 2.5  # magnitude 1 * 2.5


@pytest.mark.asyncio
@respx.mock
async def test_get_incidents_returns_empty_list_on_no_incidents():
    respx.get(INCIDENTS_URL).mock(return_value=httpx.Response(200, json={"incidents": []}))

    provider = TomTomTrafficProvider(api_key="test-key")
    incidents = await provider.get_incidents(80.0, 12.9, 80.3, 13.0)

    assert incidents == []
