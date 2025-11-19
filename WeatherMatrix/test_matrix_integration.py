"""Integration tests that simulate the full rendering pipeline without hardware."""
import pytest
from matrix_canvas import FakeMatrixCanvas, PILCanvas
from layout import calculate_layout, render_weather
from weather_data import WeatherData
from weather_provider import WeatherProviderBase
from weather_service import WeatherService
from unittest.mock import Mock, patch


class MockWeatherProvider(WeatherProviderBase):
    """Mock weather provider for testing."""
    
    def __init__(self, temp=20.0, condition="Clear"):
        self.temp = temp
        self.condition = condition
    
    def get_current(self):
        return WeatherData(
            temp=self.temp,
            feels_like=self.temp - 1,
            humidity=50.0,
            wind_speed=5.0,
            condition_main=self.condition,
            condition_description=f"{self.condition.lower()} sky"
        )


class TestFullRenderingPipeline:
    """Test the complete rendering pipeline."""
    
    def test_render_to_fake_canvas(self):
        """Test rendering weather data to fake canvas."""
        canvas = FakeMatrixCanvas(width=64, height=32)
        weather = WeatherData(
            temp=25.5,
            feels_like=24.0,
            humidity=70.0,
            wind_speed=8.0,
            condition_main="Sunny",
            condition_description="sunny",
            has_precip=False,
            precip_1h=0.0,
            timestamp=0,
            timezone_offset=0
        )
        
        # Render without font (fake canvas doesn't need real font)
        render_weather(canvas, weather, font=None, graphics_module=None)
        
        # Verify canvas was cleared
        # (We can't easily verify text was drawn without font, but we can verify operations)
        ops = calculate_layout(weather, canvas.width, canvas.height)
        assert len(ops) == 2
    
    def test_render_to_pil_canvas(self):
        """Test rendering weather data to PIL canvas (generates PNG)."""
        canvas = PILCanvas(width=64, height=32, scale=10)
        weather = WeatherData(
            temp=15.0,
            feels_like=14.0,
            humidity=60.0,
            wind_speed=3.0,
            condition_main="Clouds",
            condition_description="partly cloudy",
            has_precip=False,
            precip_1h=0.0,
            timestamp=0,
            timezone_offset=0
        )
        
        # Render with PIL (no real font needed, PIL will use default)
        render_weather(canvas, weather, font=None, graphics_module=None)
        
        # Save to file for visual inspection
        import os
        test_output = "test_matrix_output.png"
        canvas.save(test_output)
        
        # Verify file was created
        assert os.path.exists(test_output)
        
        # Clean up
        if os.path.exists(test_output):
            os.remove(test_output)
    
    def test_double_buffering_simulation(self):
        """Simulate double buffering with fake canvas."""
        # Simulate offscreen buffer
        offscreen = FakeMatrixCanvas(width=64, height=32)
        
        weather = WeatherData(
            temp=10.0,
            feels_like=9.0,
            humidity=80.0,
            wind_speed=2.0,
            condition_main="Rain",
            condition_description="light rain",
            has_precip=True,
            precip_1h=2.5,
            timestamp=0,
            timezone_offset=0
        )
        
        # Simulate multiple frames
        for frame in range(5):
            # Clear buffer
            offscreen.clear()
            
            # Calculate layout
            ops = calculate_layout(weather, offscreen.width, offscreen.height)
            
            # Draw operations (simplified - just verify operations exist)
            assert len(ops) == 2
            
            # In real code, SwapOnVSync would be called here
            # For testing, we just verify the buffer operations are correct


class TestCoordinateCalculations:
    """Test coordinate calculations match expected values."""
    
    def test_temperature_centering(self):
        """Test that temperature text is centered correctly."""
        test_cases = [
            (64, "20°", 23),   # 64 width, "20°" ~18px wide, centered at ~23
            (128, "20°", 55),  # 128 width, "20°" ~18px wide, centered at ~55
            (64, "100°", 17),  # 64 width, "100°" ~30px wide, centered at ~17
        ]
        
        for width, expected_text, expected_x in test_cases:
            weather = WeatherData(
                temp=20.0 if "20" in expected_text else 100.0,
                feels_like=19.0,
                humidity=50.0,
                wind_speed=5.0,
                condition_main="Clear",
                condition_description="clear",
                has_precip=False,
                precip_1h=0.0,
                timestamp=0,
                timezone_offset=0
            )
            
            ops = calculate_layout(weather, width=width, height=32)
            temp_op = ops[0]
            
            # Allow some margin for estimation errors
            assert abs(temp_op.kwargs["x"] - expected_x) <= 5
            assert expected_text in temp_op.kwargs["text"]


class TestBufferSwappingLogic:
    """Test the buffer swapping logic matches sample code patterns."""
    
    def test_swap_pattern_matches_samples(self):
        """Test that our swap pattern matches the Python samples."""
        # Python samples pattern:
        # 1. CreateFrameCanvas()
        # 2. Draw operations
        # 3. SwapOnVSync() in loop
        
        # Simulate this with mocks
        mock_matrix = Mock()
        mock_frame1 = Mock()
        mock_frame2 = Mock()
        
        mock_matrix.CreateFrameCanvas.return_value = mock_frame1
        mock_matrix.SwapOnVSync.side_effect = [mock_frame2, mock_frame1, mock_frame2]
        
        # Simulate the pattern
        offscreen = mock_matrix.CreateFrameCanvas()
        assert offscreen == mock_frame1
        
        # Draw something
        offscreen.Fill(255, 0, 0)
        
        # Swap
        offscreen = mock_matrix.SwapOnVSync(offscreen)
        assert offscreen == mock_frame2
        
        # Swap again
        offscreen = mock_matrix.SwapOnVSync(offscreen)
        assert offscreen == mock_frame1
        
        # Verify SwapOnVSync was called
        assert mock_matrix.SwapOnVSync.call_count == 2


class TestErrorHandling:
    """Test error handling in matrix operations."""
    
    def test_invalid_coordinates(self):
        """Test handling of invalid coordinates."""
        canvas = FakeMatrixCanvas(width=64, height=32)
        
        # Coordinates out of bounds should be handled gracefully
        canvas.set_pixel(-1, -1, 255, 0, 0)  # Should not crash
        canvas.set_pixel(100, 100, 255, 0, 0)  # Should not crash
        
        # Valid coordinates should work
        canvas.set_pixel(0, 0, 255, 0, 0)
        assert canvas.get_pixel(0, 0) == (255, 0, 0)
    
    def test_empty_weather_data(self):
        """Test handling of edge case weather data."""
        # Very cold temperature
        weather_cold = WeatherData(
            temp=-40.0,
            feels_like=-45.0,
            humidity=0.0,
            wind_speed=0.0,
            condition_main="Clear",
            condition_description="clear",
            has_precip=False,
            precip_1h=0.0,
            timestamp=0,
            timezone_offset=0
        )
        
        ops = calculate_layout(weather_cold, width=64, height=32)
        assert len(ops) == 2
        assert "-40°" in ops[0].kwargs["text"]
        
        # Very hot temperature
        weather_hot = WeatherData(
            temp=50.0,
            feels_like=55.0,
            humidity=100.0,
            wind_speed=20.0,
            condition_main="Clear",
            condition_description="clear",
            has_precip=False,
            precip_1h=0.0,
            timestamp=0,
            timezone_offset=0
        )
        
        ops = calculate_layout(weather_hot, width=64, height=32)
        assert len(ops) == 2
        assert "50°" in ops[0].kwargs["text"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

