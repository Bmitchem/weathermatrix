#!/usr/bin/env python3
"""Main entry point for weather matrix display."""
import argparse
import os
import signal
import sys
import time
from typing import Optional

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, skip loading .env file
    pass

# Try to import matrix libraries (will fail gracefully if not available)
try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
    MATRIX_AVAILABLE = True
except ImportError:
    MATRIX_AVAILABLE = False
    print("Warning: rgbmatrix not available. Use --backend=fake for testing.")

from weather_provider import WeatherProviderBase
from openweather_provider import OpenWeatherProvider
from weather_service import WeatherService
from matrix_canvas import MatrixCanvas, RealMatrixCanvas, FakeMatrixCanvas, PILCanvas
from layout import render_weather


class WeatherMatrixDisplay:
    """Main application class for weather matrix display."""
    
    def __init__(
        self,
        weather_service: WeatherService,
        canvas: MatrixCanvas,
        font_path: Optional[str] = None,
        backend: str = "pi"
    ):
        """
        Initialize weather matrix display.
        
        Args:
            weather_service: Weather service instance
            canvas: Matrix canvas (real or fake)
            font_path: Path to BDF font file
            backend: Backend type ("pi" or "fake")
        """
        self.weather_service = weather_service
        self.canvas = canvas
        self.backend = backend
        self.running = True
        
        # Load font if available
        self.font = None
        if MATRIX_AVAILABLE and font_path and backend == "pi":
            self.font = graphics.Font()
            if not self.font.LoadFont(font_path):
                print(f"Warning: Could not load font {font_path}")
                self.font = None
    
    def run(self):
        """Main display loop."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        print("Weather Matrix Display starting...")
        print("Press CTRL-C to stop")
        
        # Use double buffering for real matrix
        offscreen_canvas = None
        if self.backend == "pi" and MATRIX_AVAILABLE and hasattr(self.canvas, "_matrix"):
            offscreen_canvas = self.canvas._matrix.CreateFrameCanvas()
        
        try:
            while self.running:
                try:
                    # Get latest weather data (uses cache if fresh)
                    weather = self.weather_service.get_latest()
                    
                    # Render to canvas
                    if self.backend == "pi" and MATRIX_AVAILABLE and offscreen_canvas:
                        # Use double buffering for smooth updates
                        offscreen_canvas.Clear()
                        
                        # Get layout operations
                        from layout import calculate_layout
                        ops = calculate_layout(weather, self.canvas.width, self.canvas.height)
                        
                        # Draw on offscreen canvas
                        for op in ops:
                            if op.op_type == "text" and self.font:
                                color = graphics.Color(
                                    op.kwargs["r"],
                                    op.kwargs["g"],
                                    op.kwargs["b"]
                                )
                                graphics.DrawText(
                                    offscreen_canvas,
                                    self.font,
                                    op.kwargs["x"],
                                    op.kwargs["y"],
                                    color,
                                    op.kwargs["text"]
                                )
                        
                        # Swap buffers
                        offscreen_canvas = self.canvas._matrix.SwapOnVSync(offscreen_canvas)
                    else:
                        # Fake/PIL backend or no double buffering
                        render_weather(
                            self.canvas,
                            weather,
                            self.font,
                            graphics if MATRIX_AVAILABLE else None
                        )
                        # Print ASCII representation if fake canvas
                        if isinstance(self.canvas, FakeMatrixCanvas):
                            print("\n" + self.canvas.to_ascii())
                        # Save PNG if PIL canvas
                        elif isinstance(self.canvas, PILCanvas):
                            output_file = getattr(self, "_output_file", "weather_output.png")
                            self.canvas.save(output_file)
                            print(f"Saved weather display to {output_file}")
                            # Only render once for PNG output
                            self.running = False
                    
                    # Sleep briefly before next frame
                    time.sleep(1.0)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"Error in display loop: {e}", file=sys.stderr)
                    time.sleep(5.0)  # Wait before retrying
                    
        finally:
            self.cleanup()
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\nShutting down...")
        self.running = False
    
    def cleanup(self):
        """Clean up resources."""
        if self.canvas:
            self.canvas.clear()
        print("Cleanup complete")


def create_weather_provider(args) -> WeatherProviderBase:
    """
    Create weather provider based on configuration.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        WeatherProviderBase instance
    """
    provider_name = args.provider.lower()
    
    if provider_name == "openweather":
        api_key = args.api_key or os.environ.get("OPENWEATHER_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenWeather API key required (--api-key, OPENWEATHER_API_KEY env var, or .env file)"
            )
        
        lat = args.lat or float(os.environ.get("WEATHER_LAT", "0"))
        lon = args.lon or float(os.environ.get("WEATHER_LON", "0"))
        
        if lat == 0 and lon == 0:
            raise ValueError(
                "Latitude and longitude required (--lat/--lon, WEATHER_LAT/WEATHER_LON env vars, or .env file)"
            )
        
        return OpenWeatherProvider(
            api_key=api_key,
            lat=lat,
            lon=lon,
            units=args.units or "metric",
            lang=args.lang or "en"
        )
    else:
        raise ValueError(f"Unknown weather provider: {provider_name}")


def create_matrix_canvas(args, backend: str) -> MatrixCanvas:
    """
    Create matrix canvas based on backend type.
    
    Args:
        args: Parsed command-line arguments
        backend: Backend type ("pi", "fake", or "png")
        
    Returns:
        MatrixCanvas instance
    """
    if backend == "fake":
        return FakeMatrixCanvas(
            width=args.led_cols or 64,
            height=args.led_rows or 32
        )
    elif backend == "png":
        return PILCanvas(
            width=args.led_cols or 64,
            height=args.led_rows or 32,
            scale=10  # 10x scale for visibility
        )
    
    elif backend == "pi":
        if not MATRIX_AVAILABLE:
            raise RuntimeError("rgbmatrix library not available. Install it or use --backend=fake")
        
        options = RGBMatrixOptions()
        
        # Set matrix options from command-line args
        if args.led_gpio_mapping:
            options.hardware_mapping = args.led_gpio_mapping
        options.rows = args.led_rows or 32
        options.cols = args.led_cols or 64
        options.chain_length = args.led_chain or 1
        options.parallel = args.led_parallel or 1
        options.row_address_type = args.led_row_addr_type or 0
        options.multiplexing = args.led_multiplexing or 0
        options.pwm_bits = args.led_pwm_bits or 11
        options.brightness = args.led_brightness or 100
        options.pwm_lsb_nanoseconds = args.led_pwm_lsb_nanoseconds or 130
        options.led_rgb_sequence = args.led_rgb_sequence or "RGB"
        options.pixel_mapper_config = args.led_pixel_mapper or ""
        options.panel_type = args.led_panel_type or ""
        
        if args.led_show_refresh:
            options.show_refresh_rate = True
        
        if args.led_slowdown_gpio is not None:
            options.gpio_slowdown = args.led_slowdown_gpio
        
        if args.led_no_hardware_pulse:
            options.disable_hardware_pulsing = True
        
        if not args.led_no_drop_privs:
            options.drop_privileges = True
        
        matrix = RGBMatrix(options=options)
        return RealMatrixCanvas(matrix)
    
    else:
        raise ValueError(f"Unknown backend: {backend}")


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Display weather data on RGB LED matrix"
    )
    
    # Weather configuration
    parser.add_argument(
        "--provider",
        default=os.environ.get("WEATHER_PROVIDER", "openweather"),
        help="Weather provider (default: openweather)"
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="OpenWeather API key (or set OPENWEATHER_API_KEY env var)"
    )
    parser.add_argument(
        "--lat",
        type=float,
        default=None,
        help="Latitude (or set WEATHER_LAT env var)"
    )
    parser.add_argument(
        "--lon",
        type=float,
        default=None,
        help="Longitude (or set WEATHER_LON env var)"
    )
    parser.add_argument(
        "--units",
        choices=["metric", "imperial", "standard"],
        default=None,
        help="Temperature units (default: metric)"
    )
    parser.add_argument(
        "--lang",
        default=None,
        help="Language code for descriptions (default: en)"
    )
    parser.add_argument(
        "--cache-ttl",
        type=int,
        default=600,
        help="Cache TTL in seconds (default: 600)"
    )
    
    # Display configuration
    parser.add_argument(
        "--font",
        default=None,
        help="Path to BDF font file (default: fonts/7x13.bdf in project directory)"
    )
    parser.add_argument(
        "--backend",
        choices=["pi", "fake", "png"],
        default="pi",
        help="Backend type: pi for real hardware, fake for ASCII testing, png for PNG output (default: pi)"
    )
    parser.add_argument(
        "--output",
        default="weather_output.png",
        help="Output PNG filename when using --backend=png (default: weather_output.png)"
    )
    
    # Matrix hardware options (mirroring samplebase.py)
    parser.add_argument("-r", "--led-rows", type=int, default=32, help="Display rows")
    parser.add_argument("--led-cols", type=int, default=64, help="Panel columns")
    parser.add_argument("-c", "--led-chain", type=int, default=1, help="Daisy-chained boards")
    parser.add_argument("-P", "--led-parallel", type=int, default=1, help="Parallel chains")
    parser.add_argument("-p", "--led-pwm-bits", type=int, default=11, help="PWM bits")
    parser.add_argument("-b", "--led-brightness", type=int, default=100, help="Brightness")
    parser.add_argument("-m", "--led-gpio-mapping", help="Hardware mapping")
    parser.add_argument("--led-scan-mode", type=int, choices=[0, 1], default=0)
    parser.add_argument("--led-pwm-lsb-nanoseconds", type=int, default=130)
    parser.add_argument("--led-show-refresh", action="store_true")
    parser.add_argument("--led-slowdown-gpio", type=int, default=1)
    parser.add_argument("--led-no-hardware-pulse", action="store_true")
    parser.add_argument("--led-rgb-sequence", default="RGB")
    parser.add_argument("--led-pixel-mapper", default="")
    parser.add_argument("--led-row-addr-type", type=int, choices=[0, 1, 2, 3, 4], default=0)
    parser.add_argument("--led-multiplexing", type=int, default=0)
    parser.add_argument("--led-panel-type", default="")
    parser.add_argument("--led-no-drop-privs", action="store_true")
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    try:
        # Create weather provider and service
        provider = create_weather_provider(args)
        weather_service = WeatherService(
            provider=provider,
            cache_ttl_seconds=args.cache_ttl
        )
        
        # Create matrix canvas
        canvas = create_matrix_canvas(args, args.backend)
        
        # Default font path if not specified
        font_path = args.font
        if not font_path and args.backend == "pi":
            # Use local font file
            script_dir = os.path.dirname(os.path.abspath(__file__))
            default_font = os.path.join(script_dir, "fonts", "7x13.bdf")
            if os.path.exists(default_font):
                font_path = default_font
            else:
                print(f"Warning: Default font not found at {default_font}")
                print("Font rendering may not work correctly.")
        
        # Create and run display
        display = WeatherMatrixDisplay(
            weather_service=weather_service,
            canvas=canvas,
            font_path=font_path,
            backend=args.backend
        )
        
        # Set output file for PNG backend
        if args.backend == "png":
            display._output_file = args.output
        
        display.run()
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

