import pytest

from app.api.deps import get_geocoding_provider
from app.core.config import Settings
from app.geocoding.exceptions import GeocodingConfigurationError
from app.geocoding.nominatim_provider import NominatimProvider
from app.geocoding.tomtom_provider import TomTomGeocodingProvider


def _settings(**overrides) -> Settings:
    return Settings(**overrides)


def test_geocoding_provider_defaults_to_tomtom():
    provider = get_geocoding_provider(_settings(tomtom_api_key="key"))
    assert isinstance(provider, TomTomGeocodingProvider)


def test_geocoding_provider_selects_nominatim():
    provider = get_geocoding_provider(_settings(geocoding_provider="nominatim"))
    assert isinstance(provider, NominatimProvider)


def test_geocoding_provider_rejects_unknown_name():
    with pytest.raises(GeocodingConfigurationError):
        get_geocoding_provider(_settings(geocoding_provider="bing"))
