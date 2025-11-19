#!/usr/bin/env python3
"""Main entry point for weather matrix display."""
import argparse
import logging
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
            # Ensure font_path is absolute
            if not os.path.isabs(font_path):
                font_path = os.path.abspath(font_path)
            
            # Verify font file exists and is readable
            if not os.path.exists(font_path):
                print(f"Error: Font file does not exist: {font_path}")
            elif not os.access(font_path, os.R_OK):
                print(f"Error: Font file is not readable: {font_path}")
            else:
                # Verify it's a BDF file (check extension and first few bytes)
                if not font_path.lower().endswith('.bdf'):
                    print(f"Warning: Font file does not have .bdf extension: {font_path}")
                
                self.font = graphics.Font()
                try:
                    if not self.font.LoadFont(font_path):
                        print(f"Warning: LoadFont returned False for {font_path}")
                        self.font = None
                    else:
                        print(f"Successfully loaded font: {font_path}")
                except Exception as e:
                    print(f"Error loading font {font_path}: {e}")
                    print(f"Font path exists: {os.path.exists(font_path)}")
                    print(f"Font file readable: {os.access(font_path, os.R_OK)}")
                    if os.path.exists(font_path):
                        print(f"Font file size: {os.path.getsize(font_path)} bytes")
                        # Try to read first line to verify it's a valid BDF file
                        try:
                            with open(font_path, 'r') as f:
                                first_line = f.readline().strip()
                                print(f"First line of font file: {first_line[:50]}")
                                if not first_line.startswith('STARTFONT'):
                                    print("Warning: Font file may not be a valid BDF file")
                        except Exception as read_err:
                            print(f"Error reading font file: {read_err}")
                    self.font = None
    
    def run(self):
        """Main display loop."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logging.info("Weather Matrix Display starting...")
        logging.info(f"Backend: {self.backend}")
        logging.info(f"Canvas size: {self.canvas.width}x{self.canvas.height}")
        logging.info(f"Font loaded: {self.font is not None}")
        print("Weather Matrix Display starting...")
        print("Press CTRL-C to stop")
        
        # Use double buffering for real matrix
        offscreen_canvas = None
        if self.backend == "pi" and MATRIX_AVAILABLE and hasattr(self.canvas, "_matrix"):
            offscreen_canvas = self.canvas._matrix.CreateFrameCanvas()
        
        try:
            frame_count = 0
            while self.running:
                try:
                    frame_count += 1
                    logging.debug(f"Frame {frame_count}: Fetching weather data...")
                    
                    # Get latest weather data (uses cache if fresh)
                    weather = self.weather_service.get_latest()
                    
                    logging.info(f"Frame {frame_count}: Weather data - Temp: {weather.temp}°C, Condition: {weather.condition_main}, "
                                f"Humidity: {weather.humidity}%, Wind: {weather.wind_speed} m/s")
                    
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
                        logging.debug(f"Frame {frame_count}: Rendered and swapped buffers")
                    else:
                        # Fake/PIL backend or no double buffering
                        logging.debug(f"Frame {frame_count}: Rendering to {self.backend} backend...")
                        render_weather(
                            self.canvas,
                            weather,
                            self.font,
                            graphics if MATRIX_AVAILABLE else None
                        )
                        # Print ASCII representation if fake canvas
                        if isinstance(self.canvas, FakeMatrixCanvas):
                            if frame_count % 10 == 1:  # Print every 10th frame to reduce spam
                                print(f"\nFrame {frame_count}:")
                                print(self.canvas.to_ascii())
                        # Save PNG if PIL canvas
                        elif isinstance(self.canvas, PILCanvas):
                            output_file = getattr(self, "_output_file", "weather_output.png")
                            self.canvas.save(output_file)
                            logging.info(f"Saved weather display to {output_file}")
                            print(f"Saved weather display to {output_file}")
                            # Only render once for PNG output
                            self.running = False
                    
                    # Sleep briefly before next frame
                    time.sleep(1.0)
                    
                except KeyboardInterrupt:
                    logging.info("Interrupted by user")
                    break
                except Exception as e:
                    logging.error(f"Error in display loop (frame {frame_count}): {e}", exc_info=True)
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
        logging.info("Cleaning up resources...")
        if self.canvas:
            self.canvas.clear()
            logging.debug("Canvas cleared")
        logging.info("Cleanup complete")
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
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)"
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


def setup_logging(verbose: bool = False):
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Main entry point."""
    args = parse_args()
    
    # Setup logging
    setup_logging(verbose=args.verbose)
    
    logging.info("=" * 60)
    logging.info("Weather Matrix Display Starting")
    logging.info("=" * 60)
    
    try:
        logging.info(f"Configuration:")
        logging.info(f"  Provider: {args.provider}")
        logging.info(f"  Location: lat={args.lat or os.environ.get('WEATHER_LAT', 'N/A')}, lon={args.lon or os.environ.get('WEATHER_LON', 'N/A')}")
        logging.info(f"  Units: {args.units or 'metric'}")
        logging.info(f"  Cache TTL: {args.cache_ttl}s")
        logging.info(f"  Backend: {args.backend}")
        logging.info(f"  Matrix: {args.led_rows}x{args.led_cols}")
        
        # Create weather provider and service
        provider = create_weather_provider(args)
        logging.info("Weather provider created successfully")
        
        weather_service = WeatherService(
            provider=provider,
            cache_ttl_seconds=args.cache_ttl
        )
        logging.info(f"Weather service initialized (cache TTL: {args.cache_ttl}s)")
        
        # Create matrix canvas
        canvas = create_matrix_canvas(args, args.backend)
        logging.info(f"Matrix canvas created: {canvas.width}x{canvas.height}")
        
        # Default font path if not specified
        font_path = args.font
        if not font_path and args.backend == "pi":
            # Use local font file - resolve path relative to script location
            script_dir = os.path.dirname(os.path.abspath(__file__))
            default_font = os.path.join(script_dir, "fonts", "7x13.bdf")
            # Normalize and make absolute
            default_font = os.path.abspath(os.path.normpath(default_font))
            if os.path.exists(default_font):
                font_path = default_font
            else:
                print(f"Warning: Default font not found at {default_font}")
                print(f"Script directory: {script_dir}")
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

