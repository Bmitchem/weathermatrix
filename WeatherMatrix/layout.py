"""Layout and rendering logic for weather display - pure functions for testability."""
from typing import List, Tuple, Optional
from weather_data import WeatherData


class DrawOp:
    """Represents a drawing operation (for testing/layout calculation)."""
    def __init__(self, op_type: str, **kwargs):
        self.op_type = op_type
        self.kwargs = kwargs


def get_temperature_color(temp_c: float) -> Tuple[int, int, int]:
    """
    Get RGB color for temperature using a simple gradient.
    
    Cold (< 0°C) = blue
    Cool (0-15°C) = cyan
    Mild (15-25°C) = green/yellow
    Warm (25-35°C) = yellow/orange
    Hot (> 35°C) = red
    
    Args:
        temp_c: Temperature in Celsius
        
    Returns:
        Tuple of (r, g, b) values (0-255)
    """
    if temp_c < 0:
        # Cold: blue
        return (0, 0, 255)
    elif temp_c < 15:
        # Cool: blue to cyan
        ratio = temp_c / 15.0
        return (0, int(255 * ratio), 255)
    elif temp_c < 25:
        # Mild: cyan to green to yellow
        ratio = (temp_c - 15) / 10.0
        return (int(255 * ratio), 255, int(255 * (1 - ratio)))
    elif temp_c < 35:
        # Warm: yellow to orange
        ratio = (temp_c - 25) / 10.0
        return (255, int(255 * (1 - ratio * 0.5)), 0)
    else:
        # Hot: orange to red
        ratio = min((temp_c - 35) / 10.0, 1.0)
        return (255, int(255 * (1 - ratio)), 0)


def get_condition_text(weather: WeatherData) -> str:
    """
    Get short text representation of weather condition.
    
    Args:
        weather: Weather data
        
    Returns:
        Short condition string (e.g., "Cloudy", "Rain", "Clear")
    """
    main = weather.condition_main.lower()
    
    # Map common conditions to short display strings
    condition_map = {
        "clear": "Clear",
        "clouds": "Cloudy",
        "rain": "Rain",
        "drizzle": "Drizzle",
        "thunderstorm": "Storm",
        "snow": "Snow",
        "mist": "Mist",
        "fog": "Fog",
        "haze": "Haze",
    }
    
    return condition_map.get(main, weather.condition_main.capitalize())


def calculate_layout(weather: WeatherData, width: int = 64, height: int = 32) -> List[DrawOp]:
    """
    Calculate layout operations for weather display.
    
    This is a pure function that returns drawing operations,
    making it easy to test without actual rendering.
    
    Args:
        weather: Weather data to display
        width: Canvas width
        height: Canvas height
        
    Returns:
        List of DrawOp objects representing what to draw
    """
    ops = []
    
    # Line 1: Temperature (centered, top)
    temp_text = f"{int(weather.temp)}°"
    temp_color = get_temperature_color(weather.temp)
    
    # Estimate text width (rough: ~6 pixels per character for 7x13 font)
    # We'll center it approximately
    text_width_estimate = len(temp_text) * 6
    temp_x = max(0, (width - text_width_estimate) // 2)
    # Y coordinate is the top position where we want text to start
    # DrawText will add font.baseline() to this, so y=0 means text starts at top
    # For first line, use y=0 to start at the very top
    temp_y = 0  # Top position for first line (DrawText adds baseline)
    
    ops.append(DrawOp(
        "text",
        text=temp_text,
        x=temp_x,
        y=temp_y,
        r=temp_color[0],
        g=temp_color[1],
        b=temp_color[2]
    ))
    
    # Line 2: Condition text (centered, bottom)
    condition_text = get_condition_text(weather)
    condition_x = max(0, (width - len(condition_text) * 6) // 2)
    # Y coordinate for second line - position near bottom
    # DrawText adds font.baseline(), so y=14 means baseline at y=14+11=25
    # For 32-row display with font height 13, y=14 puts text roughly at y=14 to y=27
    condition_y = 14  # Top position for second line (DrawText adds baseline)
    
    # Use neutral white/gray for condition
    ops.append(DrawOp(
        "text",
        text=condition_text,
        x=condition_x,
        y=condition_y,
        r=200,
        g=200,
        b=200
    ))
    
    return ops


def render_weather(
    canvas,
    weather: WeatherData,
    font,
    graphics_module=None
) -> None:
    """
    Render weather data onto a canvas.
    
    Args:
        canvas: MatrixCanvas instance (real or fake)
        weather: Weather data to display
        font: Font object from rgbmatrix.graphics (or None for fake canvas)
        graphics_module: rgbmatrix.graphics module (or None for fake canvas)
    """
    canvas.clear()
    
    # Get layout operations
    ops = calculate_layout(weather, canvas.width, canvas.height)
    
    # Execute drawing operations
    for op in ops:
        if op.op_type == "text":
            if graphics_module and font:
                # Real matrix rendering - need to get the underlying matrix object
                matrix_obj = canvas._matrix if hasattr(canvas, "_matrix") else canvas
                color = graphics_module.Color(
                    op.kwargs["r"],
                    op.kwargs["g"],
                    op.kwargs["b"]
                )
                # DrawText signature: (canvas, font, x, y, color, text)
                graphics_module.DrawText(
                    matrix_obj,
                    font,
                    op.kwargs["x"],
                    op.kwargs["y"],
                    color,
                    op.kwargs["text"]
                )
            else:
                # Fake/PIL canvas - try to draw text if canvas supports it
                if hasattr(canvas, "draw_text"):
                    canvas.draw_text(
                        op.kwargs["x"],
                        op.kwargs["y"],
                        op.kwargs["text"],
                        op.kwargs["r"],
                        op.kwargs["g"],
                        op.kwargs["b"]
                    )
                # Otherwise skip text rendering
                pass

