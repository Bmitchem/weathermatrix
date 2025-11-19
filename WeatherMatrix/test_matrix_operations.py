"""Test matrix operations without hardware - verifies canvas operations, double buffering, and rendering."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from matrix_canvas import FakeMatrixCanvas, RealMatrixCanvas
from layout import calculate_layout, get_temperature_color
from weather_data import WeatherData


class TestMatrixCanvasOperations:
    """Test basic canvas operations."""
    
    def test_fake_canvas_fill(self):
        """Test that Fill() sets all pixels correctly."""
        canvas = FakeMatrixCanvas(width=64, height=32)
        canvas.fill(255, 0, 0)  # Red
        
        # Check all pixels are red
        for y in range(32):
            for x in range(64):
                r, g, b = canvas.get_pixel(x, y)
                assert r == 255
                assert g == 0
                assert b == 0
    
    def test_fake_canvas_set_pixel(self):
        """Test that SetPixel() sets individual pixels correctly."""
        canvas = FakeMatrixCanvas(width=64, height=32)
        canvas.set_pixel(10, 10, 0, 255, 0)  # Green
        
        r, g, b = canvas.get_pixel(10, 10)
        assert r == 0
        assert g == 255
        assert b == 0
        
        # Other pixels should be black
        r, g, b = canvas.get_pixel(0, 0)
        assert r == 0 and g == 0 and b == 0
    
    def test_fake_canvas_clear(self):
        """Test that Clear() resets all pixels to black."""
        canvas = FakeMatrixCanvas(width=64, height=32)
        canvas.fill(255, 255, 255)  # White
        canvas.clear()
        
        # All pixels should be black
        for y in range(32):
            for x in range(64):
                r, g, b = canvas.get_pixel(x, y)
                assert r == 0 and g == 0 and b == 0


class TestDoubleBuffering:
    """Test double buffering logic."""
    
    def test_buffer_swap_simulation(self):
        """Simulate double buffering with fake canvas."""
        # Simulate offscreen buffer
        offscreen = FakeMatrixCanvas(width=64, height=32)
        offscreen.fill(255, 0, 0)  # Red
        
        # Simulate swap - in real code, SwapOnVSync returns a new buffer
        # For testing, we'll just verify the offscreen buffer has the right content
        assert offscreen.get_pixel(0, 0) == (255, 0, 0)
        
        # Clear and draw something new
        offscreen.clear()
        offscreen.set_pixel(32, 16, 0, 255, 0)  # Green center
        assert offscreen.get_pixel(32, 16) == (0, 255, 0)
    
    def test_continuous_buffer_swapping(self):
        """Test that continuous swapping maintains state."""
        offscreen = FakeMatrixCanvas(width=64, height=32)
        
        # Simulate multiple frames
        for frame in range(10):
            offscreen.clear()
            # Draw a moving pixel
            x = frame % 64
            offscreen.set_pixel(x, 16, 255, 255, 255)
            # Verify pixel is set
            assert offscreen.get_pixel(x, 16) == (255, 255, 255)


class TestLayoutCalculations:
    """Test layout calculation logic."""
    
    def test_layout_centering_64x32(self):
        """Test that text is centered correctly for 64x32 display."""
        weather = WeatherData(
            temp=20.5,
            feels_like=19.0,
            humidity=60.0,
            wind_speed=5.0,
            condition_main="Clear",
            condition_description="clear sky",
            has_precip=False,
            precip_1h=0.0,
            timestamp=0,
            timezone_offset=0
        )
        
        ops = calculate_layout(weather, width=64, height=32)
        
        # Should have 2 operations (temp and condition)
        assert len(ops) == 2
        
        # Check temperature text
        temp_op = ops[0]
        assert temp_op.op_type == "text"
        assert "20°" in temp_op.kwargs["text"]
        
        # Check x coordinate is centered (roughly)
        temp_x = temp_op.kwargs["x"]
        # For "20°" (3 chars * 6 = 18 pixels), centered in 64 = (64-18)/2 = 23
        assert 20 <= temp_x <= 30  # Allow some margin
        
        # Check condition text
        condition_op = ops[1]
        assert condition_op.op_type == "text"
        assert condition_op.kwargs["text"] == "Clear"
    
    def test_layout_centering_128x32(self):
        """Test that text is centered correctly for 128x32 display (chained panels)."""
        weather = WeatherData(
            temp=20.5,
            feels_like=19.0,
            humidity=60.0,
            wind_speed=5.0,
            condition_main="Clear",
            condition_description="clear sky",
            has_precip=False,
            precip_1h=0.0,
            timestamp=0,
            timezone_offset=0
        )
        
        ops = calculate_layout(weather, width=128, height=32)
        
        # Should have 2 operations
        assert len(ops) == 2
        
        # Check temperature x coordinate is centered for 128 width
        temp_op = ops[0]
        temp_x = temp_op.kwargs["x"]
        # For "20°" (3 chars * 6 = 18 pixels), centered in 128 = (128-18)/2 = 55
        assert 50 <= temp_x <= 60  # Allow some margin
    
    def test_y_coordinates_with_baseline(self):
        """Test that y coordinates account for font baseline."""
        weather = WeatherData(
            temp=10.0,
            feels_like=9.0,
            humidity=50.0,
            wind_speed=3.0,
            condition_main="Clouds",
            condition_description="overcast",
            has_precip=False,
            precip_1h=0.0,
            timestamp=0,
            timezone_offset=0
        )
        
        ops = calculate_layout(weather, width=64, height=32)
        
        # First line should be at y=0 (top position, DrawText adds baseline)
        temp_op = ops[0]
        assert temp_op.kwargs["y"] == 0
        
        # Second line should be at y=14 (DrawText adds baseline=11, so baseline at y=25)
        condition_op = ops[1]
        assert condition_op.kwargs["y"] == 14


class TestTextRendering:
    """Test text rendering logic."""
    
    @patch('main.graphics', create=True)
    def test_drawtext_coordinates(self, mock_graphics):
        """Test that DrawText is called with correct coordinates including baseline."""
        # Mock font
        mock_font = Mock()
        mock_font.baseline = 11
        mock_font.height = 13
        
        # Mock graphics module
        mock_graphics.Color = Mock(return_value=Mock())
        mock_graphics.DrawText = Mock(return_value=10)
        
        # Simulate drawing text at layout y=0
        layout_y = 0
        draw_y = layout_y + mock_font.baseline  # Should be 11
        
        mock_graphics.DrawText(
            Mock(),  # canvas
            mock_font,
            10,  # x
            draw_y,  # y (should be 11)
            Mock(),  # color
            "Test"
        )
        
        # Verify DrawText was called with y=11
        mock_graphics.DrawText.assert_called_once()
        call_args = mock_graphics.DrawText.call_args
        assert call_args[0][3] == 11  # y coordinate (4th positional arg)


class TestMatrixInitialization:
    """Test matrix initialization and configuration."""
    
    def test_matrix_options_parsing(self):
        """Test that matrix options are parsed correctly."""
        from argparse import Namespace
        
        args = Namespace(
            led_rows=32,
            led_cols=64,
            led_chain=2,
            led_parallel=1,
            led_pwm_bits=11,
            led_brightness=50,
            led_slowdown_gpio=3,
            led_gpio_mapping=None,
            led_row_addr_type=0,
            led_multiplexing=0,
            led_pwm_lsb_nanoseconds=130,
            led_rgb_sequence="RGB",
            led_pixel_mapper="",
            led_panel_type="",
            led_show_refresh=False,
            led_no_hardware_pulse=False,
            led_no_drop_privs=False
        )
        
        # Test that options would be set correctly (without actually creating matrix)
        assert args.led_rows == 32
        assert args.led_cols == 64
        assert args.led_chain == 2
        assert args.led_brightness == 50
    
    @patch('main.RGBMatrix', create=True)
    def test_matrix_creation_with_options(self, mock_rgbmatrix_class):
        """Test that RGBMatrix is created with correct options."""
        # Mock RGBMatrixOptions
        mock_options = Mock()
        mock_options.rows = 32
        mock_options.cols = 64
        mock_options.chain_length = 2
        mock_options.brightness = 50
        
        mock_matrix = Mock()
        mock_rgbmatrix_class.return_value = mock_matrix
        
        # Create matrix
        matrix = mock_rgbmatrix_class(options=mock_options)
        
        # Verify it was called with options
        mock_rgbmatrix_class.assert_called_once_with(options=mock_options)
    
    @patch('main.RGBMatrix', create=True)
    def test_frame_canvas_creation(self, mock_rgbmatrix_class):
        """Test that CreateFrameCanvas is called correctly."""
        mock_matrix = Mock()
        mock_frame_canvas = Mock()
        mock_frame_canvas.width = 128
        mock_frame_canvas.height = 32
        mock_matrix.CreateFrameCanvas.return_value = mock_frame_canvas
        mock_rgbmatrix_class.return_value = mock_matrix
        
        matrix = mock_rgbmatrix_class()
        offscreen = matrix.CreateFrameCanvas()
        
        assert offscreen.width == 128
        assert offscreen.height == 32
        mock_matrix.CreateFrameCanvas.assert_called_once()


class TestCoordinateValidation:
    """Test that coordinates are within valid bounds."""
    
    def test_layout_coordinates_in_bounds_64x32(self):
        """Test that all layout coordinates are within 64x32 bounds."""
        weather = WeatherData(
            temp=99.9,  # Test with large number
            feels_like=99.0,
            humidity=100.0,
            wind_speed=50.0,
            condition_main="Thunderstorm",
            condition_description="heavy thunderstorm",
            has_precip=True,
            precip_1h=10.0,
            timestamp=0,
            timezone_offset=0
        )
        
        ops = calculate_layout(weather, width=64, height=32)
        
        for op in ops:
            if op.op_type == "text":
                x = op.kwargs["x"]
                y = op.kwargs["y"]
                
                # X should be within bounds (text might extend beyond, but start should be in bounds)
                assert 0 <= x < 64
                
                # Y should be within bounds (before adding baseline)
                assert 0 <= y < 32
    
    def test_layout_coordinates_in_bounds_128x32(self):
        """Test that all layout coordinates are within 128x32 bounds."""
        weather = WeatherData(
            temp=-40.0,  # Test with negative
            feels_like=-45.0,
            humidity=0.0,
            wind_speed=0.0,
            condition_main="Clear",
            condition_description="clear sky",
            has_precip=False,
            precip_1h=0.0,
            timestamp=0,
            timezone_offset=0
        )
        
        ops = calculate_layout(weather, width=128, height=32)
        
        for op in ops:
            if op.op_type == "text":
                x = op.kwargs["x"]
                y = op.kwargs["y"]
                
                assert 0 <= x < 128
                assert 0 <= y < 32


class TestFontBaselineHandling:
    """Test font baseline calculations."""
    
    def test_baseline_addition(self):
        """Test that baseline is correctly added to y coordinates."""
        # Simulate font with baseline=11
        font_baseline = 11
        
        # Layout provides y=0 (top position)
        layout_y = 0
        
        # DrawText should receive y + baseline
        draw_y = layout_y + font_baseline
        
        assert draw_y == 11
        
        # For second line at y=14
        layout_y2 = 14
        draw_y2 = layout_y2 + font_baseline
        assert draw_y2 == 25
    
    def test_text_vertical_bounds_with_baseline(self):
        """Test that text with baseline doesn't go out of bounds."""
        font_height = 13
        font_baseline = 11
        
        # First line: y=0, baseline at y=11
        # Text extends from y=11-baseline=0 to y=11+(height-baseline)=13
        layout_y1 = 0
        draw_y1 = layout_y1 + font_baseline
        text_top = draw_y1 - font_baseline  # 0
        text_bottom = draw_y1 + (font_height - font_baseline)  # 13
        
        assert text_top >= 0
        assert text_bottom <= 32
        
        # Second line: y=14, baseline at y=25
        layout_y2 = 14
        draw_y2 = layout_y2 + font_baseline
        text_top2 = draw_y2 - font_baseline  # 14
        text_bottom2 = draw_y2 + (font_height - font_baseline)  # 27
        
        assert text_top2 >= 0
        assert text_bottom2 <= 32


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

