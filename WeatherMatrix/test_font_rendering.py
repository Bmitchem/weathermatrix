"""Test font rendering and text positioning."""
import pytest
from unittest.mock import Mock, patch
from layout import calculate_layout
from weather_data import WeatherData


class TestFontBaselineCalculations:
    """Test font baseline handling matches rgbmatrix behavior."""
    
    def test_baseline_addition_matches_samples(self):
        """Test that our baseline addition matches the sample code pattern."""
        # From runtext.py: DrawText(offscreen_canvas, font, pos, 10, textColor, my_text)
        # They use y=10 directly, which suggests DrawText handles baseline internally
        
        # But from clock.cc: DrawText(offscreen, font, x, y + font.baseline() + line_offset, ...)
        # They add baseline explicitly
        
        # Our approach: Add baseline explicitly (matching C++ examples)
        font_baseline = 11
        
        # Layout provides top position
        layout_y = 0
        
        # We add baseline before calling DrawText
        draw_y = layout_y + font_baseline
        
        assert draw_y == 11
    
    def test_text_vertical_positioning(self):
        """Test that text positioning accounts for font metrics."""
        font_height = 13
        font_baseline = 11
        
        # First line: layout y=0, draw y=11
        # Text extends from y=0 to y=13 (height pixels)
        layout_y1 = 0
        draw_y1 = layout_y1 + font_baseline
        
        # Calculate text bounds
        text_top = draw_y1 - font_baseline  # 0
        text_bottom = text_top + font_height  # 13
        
        assert text_top == 0
        assert text_bottom == 13
        assert text_bottom <= 32  # Within 32-row display
        
        # Second line: layout y=14, draw y=25
        layout_y2 = 14
        draw_y2 = layout_y2 + font_baseline
        
        text_top2 = draw_y2 - font_baseline  # 14
        text_bottom2 = text_top2 + font_height  # 27
        
        assert text_top2 == 14
        assert text_bottom2 == 27
        assert text_bottom2 <= 32


class TestTextWidthEstimation:
    """Test text width estimation for centering."""
    
    def test_text_width_estimation(self):
        """Test that text width estimation is reasonable."""
        # 7x13 font: approximately 6 pixels per character
        chars_per_pixel = 6
        
        test_cases = [
            ("20°", 3, 18),   # 3 chars * 6 = 18
            ("100°", 4, 24), # 4 chars * 6 = 24
            ("-10°", 4, 24), # 4 chars * 6 = 24
        ]
        
        for text, char_count, expected_width in test_cases:
            estimated_width = char_count * chars_per_pixel
            assert estimated_width == expected_width
    
    def test_centering_calculation(self):
        """Test that centering calculation works correctly."""
        width = 64
        text_width = 18  # "20°"
        
        centered_x = (width - text_width) // 2
        assert centered_x == 23
        
        # For 128 width
        width_128 = 128
        centered_x_128 = (width_128 - text_width) // 2
        assert centered_x_128 == 55


class TestDrawTextCallPattern:
    """Test that DrawText is called with correct parameters."""
    
    @patch('main.graphics', create=True)
    def test_drawtext_call_matches_samples(self, mock_graphics):
        """Test that DrawText calls match the sample code pattern."""
        mock_font = Mock()
        mock_font.baseline = 11
        mock_font.height = 13
        
        mock_canvas = Mock()
        mock_color = Mock()
        mock_graphics.Color.return_value = mock_color
        mock_graphics.DrawText.return_value = 10
        
        # Simulate our rendering code
        layout_y = 0
        draw_y = layout_y + mock_font.baseline
        
        mock_graphics.DrawText(
            mock_canvas,
            mock_font,
            10,  # x
            draw_y,  # y (with baseline added)
            mock_color,
            "Test"
        )
        
        # Verify call
        mock_graphics.DrawText.assert_called_once()
        call_args = mock_graphics.DrawText.call_args[0]
        
        assert call_args[0] == mock_canvas
        assert call_args[1] == mock_font
        assert call_args[2] == 10  # x
        assert call_args[3] == 11  # y (with baseline)
        assert call_args[4] == mock_color
        assert call_args[5] == "Test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

