"""Tests for weather_data module."""
import pytest
from datetime import datetime
from weather_data import WeatherData


def test_weather_data_creation():
    """Test creating WeatherData with required fields."""
    weather = WeatherData(
        temp=20.5,
        feels_like=19.8,
        humidity=65.0,
        wind_speed=5.2,
        condition_main="Clouds",
        condition_description="broken clouds",
        has_precip=False,
        precip_1h=0.0,
        timestamp=1609459200,
        timezone_offset=-18000
    )
    
    assert weather.temp == 20.5
    assert weather.feels_like == 19.8
    assert weather.humidity == 65.0
    assert weather.wind_speed == 5.2
    assert weather.condition_main == "Clouds"
    assert weather.condition_description == "broken clouds"
    assert weather.has_precip is False
    assert weather.precip_1h == 0.0


def test_weather_data_is_stale():
    """Test is_stale() method."""
    # Create data with old timestamp (1 hour ago)
    old_timestamp = int(datetime.utcnow().timestamp()) - 3600
    weather = WeatherData(
        temp=20.0,
        feels_like=19.0,
        humidity=60.0,
        wind_speed=5.0,
        condition_main="Clear",
        condition_description="clear sky",
        has_precip=False,
        precip_1h=0.0,
        timestamp=old_timestamp,
        timezone_offset=0
    )
    
    # Should be stale with default 15-minute threshold
    assert weather.is_stale(max_age_seconds=900) is True
    
    # Should not be stale with 2-hour threshold
    assert weather.is_stale(max_age_seconds=7200) is False


def test_weather_data_fresh():
    """Test that fresh data is not stale."""
    current_timestamp = int(datetime.utcnow().timestamp())
    weather = WeatherData(
        temp=20.0,
        feels_like=19.0,
        humidity=60.0,
        wind_speed=5.0,
        condition_main="Clear",
        condition_description="clear sky",
        has_precip=False,
        precip_1h=0.0,
        timestamp=current_timestamp,
        timezone_offset=0
    )
    
    assert weather.is_stale(max_age_seconds=900) is False

