import httpx
import pytest
import respx

from app.geocoding.exceptions import (
    GeocodingProviderTimeoutError,
    GeocodingProviderUnavailableError,
)
from app.geocoding.nominatim_provider import NominatimProvider

BASE_URL = "https://nominatim.test"


@pytest.mark.asyncio
async def test_empty_query_returns_no_results_without_calling_provider():
    provider = NominatimProvider(base_url=BASE_URL)
    assert await provider.search("   ") == []


@pytest.mark.asyncio
@respx.mock
async def test_search_parses_suggestions_and_sends_user_agent():
    route = respx.get(f"{BASE_URL}/search").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"display_name": "Chennai Central, Chennai, Tamil Nadu", "lat": "13.0827", "lon": "80.2707"},
                {"display_name": "", "lat": "1.0", "lon": "2.0"},  # blank label, should be skipped
                {"lat": "not-a-number", "lon": "2.0", "display_name": "Bad coordinate"},  # unparsable
            ],
        )
    )

    provider = NominatimProvider(base_url=BASE_URL)
    results = await provider.search("Chennai Central")

    assert route.called
    assert route.calls.last.request.headers["User-Agent"].startswith("QTrace/")
    assert len(results) == 1
    assert results[0].label == "Chennai Central, Chennai, Tamil Nadu"
    assert results[0].coordinate.latitude == 13.0827
    assert results[0].coordinate.longitude == 80.2707


@pytest.mark.asyncio
@respx.mock
async def test_search_raises_unavailable_on_http_error():
    respx.get(f"{BASE_URL}/search").mock(return_value=httpx.Response(503))

    provider = NominatimProvider(base_url=BASE_URL)
    with pytest.raises(GeocodingProviderUnavailableError):
        await provider.search("Chennai Central")


@pytest.mark.asyncio
@respx.mock
async def test_search_raises_timeout_after_retries_exhausted():
    respx.get(f"{BASE_URL}/search").mock(side_effect=httpx.TimeoutException("timed out"))

    provider = NominatimProvider(base_url=BASE_URL, max_retries=1)
    with pytest.raises(GeocodingProviderTimeoutError):
        await provider.search("Chennai Central")


@pytest.mark.asyncio
@respx.mock
async def test_throttles_between_consecutive_requests(monkeypatch):
    respx.get(f"{BASE_URL}/search").mock(return_value=httpx.Response(200, json=[]))

    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("app.geocoding.nominatim_provider.asyncio.sleep", fake_sleep)

    provider = NominatimProvider(base_url=BASE_URL)
    await provider.search("first query")
    await provider.search("second query")

    # First call has nothing to wait for; the second must respect the 1 req/sec policy.
    assert len(sleep_calls) == 1
    assert sleep_calls[0] > 0
