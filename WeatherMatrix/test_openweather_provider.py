"""Tests for OpenWeather provider."""
import pytest
import json
from unittest.mock import Mock, patch
from openweather_provider import OpenWeatherProvider, WeatherProviderError
from weather_data import WeatherData


@pytest.fixture
def sample_openweather_response():
    """Sample OpenWeather API response."""
    return {
        "coord": {"lon": -94.04, "lat": 33.44},
        "weather": [
            {
                "id": 803,
                "main": "Clouds",
                "description": "broken clouds",
                "icon": "04d"
            }
        ],
        "base": "stations",
        "main": {
            "temp": 292.55,
            "feels_like": 292.87,
            "pressure": 1014,
            "humidity": 89
        },
        "visibility": 10000,
        "wind": {"speed": 3.13, "deg": 93},
        "rain": {"1h": 2.93},
        "clouds": {"all": 53},
        "dt": 1684929490,
        "sys": {"country": "US"},
        "timezone": -18000,
        "name": "Testville",
        "id": 123
    }


@pytest.fixture
def provider():
    """Create OpenWeather provider instance."""
    return OpenWeatherProvider(
        api_key="test_key",
        lat=33.44,
        lon=-94.04,
        units="metric"
    )


def test_openweather_provider_success(provider, sample_openweather_response):
    """Test successful API call and parsing."""
    with patch('openweather_provider.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = sample_openweather_response
        mock_get.return_value = mock_response
        
        weather = provider.get_current()
        
        assert isinstance(weather, WeatherData)
        assert weather.temp == 292.55
        assert weather.feels_like == 292.87
        assert weather.humidity == 89.0
        assert weather.wind_speed == 3.13
        assert weather.condition_main == "Clouds"
        assert weather.condition_description == "broken clouds"
        assert weather.has_precip is True
        assert weather.precip_1h == 2.93
        assert weather.timestamp == 1684929490
        assert weather.timezone_offset == -18000


def test_openweather_provider_no_precipitation(provider):
    """Test parsing response without precipitation."""
    response = {
        "coord": {"lon": -94.04, "lat": 33.44},
        "weather": [
            {
                "main": "Clear",
                "description": "clear sky"
            }
        ],
        "main": {
            "temp": 20.5,
            "feels_like": 19.8,
            "humidity": 65
        },
        "wind": {"speed": 5.2},
        "dt": 1684929490,
        "timezone": -18000
    }
    
    with patch('openweather_provider.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = response
        mock_get.return_value = mock_response
        
        weather = provider.get_current()
        
        assert weather.has_precip is False
        assert weather.precip_1h == 0.0


def test_openweather_provider_snow(provider):
    """Test parsing response with snow."""
    response = {
        "coord": {"lon": -94.04, "lat": 33.44},
        "weather": [
            {
                "main": "Snow",
                "description": "light snow"
            }
        ],
        "main": {
            "temp": -5.0,
            "feels_like": -8.0,
            "humidity": 80
        },
        "wind": {"speed": 10.0},
        "snow": {
            "1h": 1.2
        },
        "dt": 1684929490,
        "timezone": -18000
    }
    
    with patch('openweather_provider.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = response
        mock_get.return_value = mock_response
        
        weather = provider.get_current()
        
        assert weather.has_precip is True
        assert weather.precip_1h == 1.2


def test_openweather_provider_http_error(provider):
    """Test handling of HTTP errors."""
    with patch('openweather_provider.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "cod": 401,
            "message": "Invalid API key"
        }
        mock_get.return_value = mock_response
        
        with pytest.raises(WeatherProviderError) as exc_info:
            provider.get_current()
        
        assert "401" in str(exc_info.value)
        assert "Invalid API key" in str(exc_info.value)


def test_openweather_provider_network_error(provider):
    """Test handling of network errors."""
    with patch('openweather_provider.requests.get') as mock_get:
        mock_get.side_effect = Exception("Connection timeout")
        
        with pytest.raises(WeatherProviderError) as exc_info:
            provider.get_current()
        
        assert "Network error" in str(exc_info.value)


def test_openweather_provider_missing_current(provider):
    """Test handling of missing main block."""
    response = {
        "coord": {"lon": -94.04, "lat": 33.44},
        "weather": [
            {
                "main": "Clear",
                "description": "clear sky"
            }
        ]
    }
    
    with patch('openweather_provider.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = response
        mock_get.return_value = mock_response
        
        with pytest.raises(WeatherProviderError) as exc_info:
            provider.get_current()
        
        assert "missing 'main' block" in str(exc_info.value)


def test_openweather_provider_missing_weather(provider):
    """Test handling of missing 'weather' array."""
    response = {
        "coord": {"lon": -94.04, "lat": 33.44},
        "main": {"temp": 20.0},
        "dt": 1684929490,
        "timezone": -18000,
        "weather": []
    }
    
    with patch('openweather_provider.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = response
        mock_get.return_value = mock_response
        
        with pytest.raises(WeatherProviderError) as exc_info:
            provider.get_current()
        
        assert "missing 'weather' array" in str(exc_info.value)

