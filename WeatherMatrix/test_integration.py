"""Integration tests - can optionally hit real API (disabled by default)."""
import os
import pytest
from openweather_provider import OpenWeatherProvider
from weather_service import WeatherService


@pytest.mark.skipif(
    not os.environ.get("OPENWEATHER_API_KEY"),
    reason="OPENWEATHER_API_KEY not set - skipping integration test"
)
def test_openweather_integration():
    """
    Integration test that hits the real OpenWeather API.
    
    Set OPENWEATHER_API_KEY environment variable to run this test.
    """
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    
    provider = OpenWeatherProvider(
        api_key=api_key,
        lat=33.44,  # Example coordinates
        lon=-94.04,
        units="metric"
    )
    
    # Should succeed
    weather = provider.get_current()
    
    assert weather.temp is not None
    assert weather.condition_main is not None
    assert weather.timestamp > 0


@pytest.mark.skipif(
    not os.environ.get("OPENWEATHER_API_KEY"),
    reason="OPENWEATHER_API_KEY not set - skipping integration test"
)
def test_weather_service_integration():
    """Integration test for WeatherService with real API."""
    api_key = os.environ.get("OPENWEATHER_API_KEY")
    
    provider = OpenWeatherProvider(
        api_key=api_key,
        lat=33.44,
        lon=-94.04,
        units="metric"
    )
    
    service = WeatherService(provider, cache_ttl_seconds=60)
    
    # First call
    weather1 = service.get_latest()
    assert weather1.temp is not None
    
    # Second call should use cache
    weather2 = service.get_latest()
    assert weather2.temp == weather1.temp

