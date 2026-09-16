import httpx
import pytest
import respx

from app.geocoding.exceptions import (
    GeocodingConfigurationError,
    GeocodingProviderTimeoutError,
    GeocodingProviderUnavailableError,
)
from app.geocoding.tomtom_provider import TomTomGeocodingProvider

SEARCH_URL_PREFIX = "https://api.tomtom.com/search/2/search/"


@pytest.mark.asyncio
async def test_search_without_api_key_raises_configuration_error():
    provider = TomTomGeocodingProvider(api_key=None)
    with pytest.raises(GeocodingConfigurationError):
        await provider.search("123 Main St")


@pytest.mark.asyncio
async def test_empty_query_returns_no_results_without_calling_provider():
    provider = TomTomGeocodingProvider(api_key="test-key")
    assert await provider.search("   ") == []


@pytest.mark.asyncio
@respx.mock
async def test_search_parses_suggestions():
    respx.get(url__startswith=SEARCH_URL_PREFIX).mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "address": {"freeformAddress": "MG Road, Bengaluru"},
                        "position": {"lat": 12.9756, "lon": 77.6068},
                    },
                    {"address": {}, "position": {"lat": 1.0, "lon": 2.0}},  # missing label, should be skipped
                ]
            },
        )
    )

    provider = TomTomGeocodingProvider(api_key="test-key")
    results = await provider.search("MG Road")

    assert len(results) == 1
    assert results[0].label == "MG Road, Bengaluru"
    assert results[0].coordinate.latitude == 12.9756
    assert results[0].coordinate.longitude == 77.6068


@pytest.mark.asyncio
@respx.mock
async def test_search_raises_unavailable_on_http_error():
    respx.get(url__startswith=SEARCH_URL_PREFIX).mock(return_value=httpx.Response(401))

    provider = TomTomGeocodingProvider(api_key="bad-key")
    with pytest.raises(GeocodingProviderUnavailableError):
        await provider.search("MG Road")


@pytest.mark.asyncio
@respx.mock
async def test_search_raises_timeout_after_retries_exhausted():
    respx.get(url__startswith=SEARCH_URL_PREFIX).mock(side_effect=httpx.TimeoutException("timed out"))

    provider = TomTomGeocodingProvider(api_key="test-key", max_retries=1)
    with pytest.raises(GeocodingProviderTimeoutError):
        await provider.search("MG Road")
