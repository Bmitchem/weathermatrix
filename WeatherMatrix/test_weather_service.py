"""Tests for weather service."""
import pytest
import time
from unittest.mock import Mock, patch
from weather_service import WeatherService
from weather_provider import WeatherProviderBase, WeatherProviderError
from weather_data import WeatherData


class MockProvider(WeatherProviderBase):
    """Mock weather provider for testing."""
    
    def __init__(self, return_data=None, raise_error=None):
        self.return_data = return_data
        self.raise_error = raise_error
        self.call_count = 0
    
    def get_current(self):
        self.call_count += 1
        if self.raise_error:
            raise self.raise_error
        return self.return_data


@pytest.fixture
def sample_weather():
    """Sample weather data."""
    return WeatherData(
        temp=20.0,
        feels_like=19.0,
        humidity=60.0,
        wind_speed=5.0,
        condition_main="Clear",
        condition_description="clear sky",
        has_precip=False,
        precip_1h=0.0,
        timestamp=int(time.time()),
        timezone_offset=0
    )


def test_weather_service_caching(sample_weather):
    """Test that service caches results."""
    provider = MockProvider(return_data=sample_weather)
    service = WeatherService(provider, cache_ttl_seconds=60)
    
    # First call should hit provider
    result1 = service.get_latest()
    assert provider.call_count == 1
    assert result1.temp == 20.0
    
    # Second call within TTL should use cache
    result2 = service.get_latest()
    assert provider.call_count == 1  # Still 1, not 2
    assert result2.temp == 20.0


def test_weather_service_cache_expiry(sample_weather):
    """Test that cache expires after TTL."""
    provider = MockProvider(return_data=sample_weather)
    service = WeatherService(provider, cache_ttl_seconds=1)  # 1 second TTL
    
    # First call
    service.get_latest()
    assert provider.call_count == 1
    
    # Wait for cache to expire
    time.sleep(1.1)
    
    # Second call should hit provider again
    service.get_latest()
    assert provider.call_count == 2


def test_weather_service_retry_on_error(sample_weather):
    """Test that service retries on transient errors."""
    provider = MockProvider(
        raise_error=WeatherProviderError("Network error")
    )
    provider.return_data = sample_weather
    
    service = WeatherService(provider, max_retries=3, retry_delay_seconds=0.1)
    
    # First call fails, but then succeeds
    def side_effect():
        if provider.call_count < 2:
            raise WeatherProviderError("Network error")
        return sample_weather
    
    provider.get_current = side_effect
    
    result = service.get_latest()
    assert result.temp == 20.0
    assert provider.call_count >= 2


def test_weather_service_no_retry_on_4xx(sample_weather):
    """Test that service doesn't retry on 4xx errors."""
    provider = MockProvider(
        raise_error=WeatherProviderError("401 Unauthorized")
    )
    
    service = WeatherService(provider, max_retries=3)
    
    with pytest.raises(WeatherProviderError):
        service.get_latest()
    
    # Should only try once (no retries for 4xx)
    assert provider.call_count == 1


def test_weather_service_fallback_to_cache(sample_weather):
    """Test that service falls back to stale cache on failure."""
    # Create provider that fails after first success
    provider = MockProvider(return_data=sample_weather)
    service = WeatherService(provider, cache_ttl_seconds=1)
    
    # First call succeeds
    result1 = service.get_latest()
    assert result1.temp == 20.0
    
    # Make provider fail
    provider.raise_error = WeatherProviderError("Network error")
    provider.return_data = None
    
    # Wait for cache to expire
    time.sleep(1.1)
    
    # Should return stale cache instead of raising
    result2 = service.get_latest()
    assert result2.temp == 20.0


def test_weather_service_no_cache_on_first_failure():
    """Test that service raises error if no cache exists."""
    provider = MockProvider(raise_error=WeatherProviderError("Network error"))
    service = WeatherService(provider, max_retries=1)
    
    with pytest.raises(WeatherProviderError):
        service.get_latest()

