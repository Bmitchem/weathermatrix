"""Tests for layout and rendering logic."""
import pytest
from weather_data import WeatherData
from layout import get_temperature_color, get_condition_text, calculate_layout


@pytest.fixture
def sample_weather():
    """Sample weather data."""
    return WeatherData(
        temp=20.0,
        feels_like=19.0,
        humidity=60.0,
        wind_speed=5.0,
        condition_main="Clouds",
        condition_description="broken clouds",
        has_precip=False,
        precip_1h=0.0,
        timestamp=1609459200,
        timezone_offset=0
    )


def test_temperature_color_cold():
    """Test color for cold temperatures."""
    color = get_temperature_color(-10.0)
    assert color == (0, 0, 255)  # Blue


def test_temperature_color_cool():
    """Test color for cool temperatures."""
    color = get_temperature_color(10.0)
    # Should be between blue and cyan
    assert color[0] == 0  # No red
    assert color[1] > 0  # Some green
    assert color[2] == 255  # Full blue


def test_temperature_color_mild():
    """Test color for mild temperatures."""
    color = get_temperature_color(20.0)
    # Should be green/yellow range
    assert color[0] > 0  # Some red
    assert color[1] == 255  # Full green
    assert color[2] >= 0  # Blue decreasing


def test_temperature_color_warm():
    """Test color for warm temperatures."""
    color = get_temperature_color(30.0)
    # Should be yellow/orange range
    assert color[0] == 255  # Full red
    assert color[1] > 0  # Some green
    assert color[2] == 0  # No blue


def test_temperature_color_hot():
    """Test color for hot temperatures."""
    color = get_temperature_color(40.0)
    # Should be red
    assert color[0] == 255  # Full red
    assert color[1] < 255  # Less green
    assert color[2] == 0  # No blue


def test_get_condition_text_clear(sample_weather):
    """Test condition text for clear weather."""
    weather = WeatherData(
        temp=20.0,
        feels_like=19.0,
        humidity=60.0,
        wind_speed=5.0,
        condition_main="Clear",
        condition_description="clear sky",
        has_precip=False,
        precip_1h=0.0,
        timestamp=1609459200,
        timezone_offset=0
    )
    assert get_condition_text(weather) == "Clear"


def test_get_condition_text_clouds(sample_weather):
    """Test condition text for cloudy weather."""
    assert get_condition_text(sample_weather) == "Cloudy"


def test_get_condition_text_rain():
    """Test condition text for rain."""
    weather = WeatherData(
        temp=15.0,
        feels_like=14.0,
        humidity=80.0,
        wind_speed=8.0,
        condition_main="Rain",
        condition_description="light rain",
        has_precip=True,
        precip_1h=2.5,
        timestamp=1609459200,
        timezone_offset=0
    )
    assert get_condition_text(weather) == "Rain"


def test_get_condition_text_unknown():
    """Test condition text for unknown condition."""
    weather = WeatherData(
        temp=20.0,
        feels_like=19.0,
        humidity=60.0,
        wind_speed=5.0,
        condition_main="Tornado",
        condition_description="tornado",
        has_precip=False,
        precip_1h=0.0,
        timestamp=1609459200,
        timezone_offset=0
    )
    # Should capitalize the main condition
    assert get_condition_text(weather) == "Tornado"


def test_calculate_layout(sample_weather):
    """Test layout calculation."""
    ops = calculate_layout(sample_weather, width=64, height=32)
    
    assert len(ops) >= 2  # At least temperature and condition
    
    # Check that we have text operations
    text_ops = [op for op in ops if op.op_type == "text"]
    assert len(text_ops) >= 2
    
    # Check temperature operation
    temp_op = next((op for op in ops if "20" in op.kwargs.get("text", "")), None)
    assert temp_op is not None
    assert temp_op.kwargs["text"] == "20°"
    
    # Check condition operation
    condition_op = next((op for op in ops if op.kwargs.get("text") == "Cloudy"), None)
    assert condition_op is not None


def test_calculate_layout_different_temps():
    """Test layout with different temperatures."""
    # Cold weather
    cold_weather = WeatherData(
        temp=-5.0,
        feels_like=-8.0,
        humidity=80.0,
        wind_speed=10.0,
        condition_main="Snow",
        condition_description="light snow",
        has_precip=True,
        precip_1h=1.0,
        timestamp=1609459200,
        timezone_offset=0
    )
    ops_cold = calculate_layout(cold_weather)
    temp_op_cold = next((op for op in ops_cold if op.op_type == "text" and "°" in op.kwargs.get("text", "")), None)
    assert temp_op_cold is not None
    assert "-5" in temp_op_cold.kwargs["text"]
    
    # Hot weather
    hot_weather = WeatherData(
        temp=38.0,
        feels_like=40.0,
        humidity=30.0,
        wind_speed=5.0,
        condition_main="Clear",
        condition_description="clear sky",
        has_precip=False,
        precip_1h=0.0,
        timestamp=1609459200,
        timezone_offset=0
    )
    ops_hot = calculate_layout(hot_weather)
    temp_op_hot = next((op for op in ops_hot if op.op_type == "text" and "°" in op.kwargs.get("text", "")), None)
    assert temp_op_hot is not None
    assert "38" in temp_op_hot.kwargs["text"]

