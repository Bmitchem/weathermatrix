"""Metro-style weather display for the RGB matrix."""
import argparse
import logging
import os
import signal
import sys
import time
from typing import Tuple

from dotenv import load_dotenv

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics
except ImportError:  # pragma: no cover - fallback used in tests/local dev
    class _GraphicsStub:  # pylint: disable=too-few-public-methods
        """Minimal graphics stub so tests can patch attributes."""

        class Font:  # pylint: disable=too-few-public-methods
            def __init__(self):
                self.height = 0
                self.baseline = 0

            def LoadFont(self, *_args, **_kwargs):
                raise RuntimeError("rgbmatrix not installed")

        @staticmethod
        def Color(r, g, b):
            return (r, g, b)

        @staticmethod
        def DrawText(*_args, **_kwargs):
            raise RuntimeError("rgbmatrix not installed")

    class _MatrixStub:  # pylint: disable=too-few-public-methods
        def __init__(self, *args, **kwargs):
            raise RuntimeError("rgbmatrix not installed")

        def Clear(self):  # pragma: no cover
            pass

    class _OptionsStub:  # pylint: disable=too-few-public-methods
        pass

    RGBMatrix = _MatrixStub  # type: ignore[assignment]
    RGBMatrixOptions = _OptionsStub  # type: ignore[assignment]
    graphics = _GraphicsStub()  # type: ignore[assignment]

from weather_service import WeatherService
from openweather_provider import OpenWeatherProvider
from weather_provider import WeatherProviderError

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FONT = os.path.join(BASE_DIR, "fonts", "7x13.bdf")
DEFAULT_LOG_FILE = os.path.join(BASE_DIR, "weather-matrix.log")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("RGB matrix weather display")
    parser.add_argument("--log-file", default=DEFAULT_LOG_FILE)
    parser.add_argument("--led-rows", type=int, default=32)
    parser.add_argument("--led-cols", type=int, default=64)
    parser.add_argument("--led-chain", type=int, default=2)
    parser.add_argument("--led-parallel", type=int, default=1)
    parser.add_argument("--led-pwm-bits", type=int, default=11)
    parser.add_argument("--led-slowdown-gpio", type=int, default=2)
    parser.add_argument("--brightness", type=int, default=80)
    parser.add_argument("--font", default=DEFAULT_FONT)
    parser.add_argument("--units", choices=["metric", "imperial", "standard"], default="metric")
    parser.add_argument("--refresh", type=float, default=30.0, help="Seconds between refreshes")
    parser.add_argument("--cache-ttl", type=int, default=600)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--retry-delay", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=10, help="HTTP timeout in seconds")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def setup_logging(log_file: str, verbose: bool) -> None:
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file)
        ]
    )


def load_config(units: str) -> Tuple[str, float, float, str]:
    load_dotenv()
    api_key = os.getenv("WEATHER_API_KEY")
    lat = os.getenv("WEATHER_LAT")
    lon = os.getenv("WEATHER_LON")
    lang = os.getenv("WEATHER_LANG", "en")

    if not api_key:
        raise SystemExit("Missing WEATHER_API_KEY in environment")
    if not lat or not lon:
        raise SystemExit("Missing WEATHER_LAT/WEATHER_LON in environment")

    try:
        lat_val = float(lat)
        lon_val = float(lon)
    except ValueError as exc:
        raise SystemExit(f"Invalid coordinates: {exc}") from exc

    logging.info("Configuration loaded: lat=%s lon=%s units=%s", lat_val, lon_val, units)
    return api_key, lat_val, lon_val, lang


def init_matrix(args: argparse.Namespace) -> RGBMatrix:
    if RGBMatrix is None:
        raise SystemExit("rgbmatrix library not available; run on the Pi")

    options = RGBMatrixOptions()
    options.rows = args.led_rows
    options.cols = args.led_cols
    options.chain_length = args.led_chain
    options.parallel = args.led_parallel
    options.pwm_bits = args.led_pwm_bits
    options.brightness = args.brightness
    options.gpio_slowdown = args.led_slowdown_gpio

    logging.info(
        "Matrix init: rows=%s cols=%s chain=%s parallel=%s pwm_bits=%s brightness=%s slowdown=%s",
        options.rows,
        options.cols,
        options.chain_length,
        options.parallel,
        options.pwm_bits,
        options.brightness,
        options.gpio_slowdown,
    )

    return RGBMatrix(options=options)


def load_font(font_path: str) -> graphics.Font:
    if graphics is None:
        raise SystemExit("rgbmatrix library not available")

    if not os.path.isabs(font_path):
        font_path = os.path.join(BASE_DIR, font_path)
    font_path = os.path.abspath(font_path)

    font = graphics.Font()
    logging.info("Loading font: %s", font_path)
    font.LoadFont(font_path)
    logging.info("Font loaded: height=%s baseline=%s", font.height, font.baseline)
    return font


def build_weather_service(api_key: str, lat: float, lon: float, args: argparse.Namespace) -> WeatherService:
    provider = OpenWeatherProvider(
        api_key=api_key,
        lat=lat,
        lon=lon,
        units=args.units,
        lang=os.getenv("WEATHER_LANG", "en"),
        timeout=args.timeout,
    )
    service = WeatherService(
        provider=provider,
        cache_ttl_seconds=args.cache_ttl,
        max_retries=args.max_retries,
        retry_delay_seconds=args.retry_delay,
    )
    logging.info("Weather service ready (cache ttl=%ss)", args.cache_ttl)
    return service


def format_weather_lines(weather) -> Tuple[str, str, str]:
    temp = f"{round(weather.temp):+d}°" if weather.temp is not None else "N/A"
    condition = weather.condition_main.title()[:18]
    feels = f"Feels {round(weather.feels_like):+d}°"
    humidity = f"Hum {int(weather.humidity)}%"
    wind = f"Wind {weather.wind_speed:.1f}m/s"
    return temp, condition, f"{feels}  {humidity}  {wind}"


def draw_weather(matrix: RGBMatrix, font: graphics.Font, weather) -> None:
    temp_text, condition_text, info_text = format_weather_lines(weather)
    matrix.Clear()

    temp_color = graphics.Color(0, 113, 255)
    condition_color = graphics.Color(220, 220, 220)
    info_color = graphics.Color(180, 180, 180)

    baseline = font.baseline
    second_line = baseline + font.height + 2
    third_line = second_line + font.height + 2

    x = 2
    temp_width = graphics.DrawText(matrix, font, x, baseline, temp_color, temp_text)
    logging.info("DrawText temp='%s' x=%s y=%s width=%s", temp_text, x, baseline, temp_width)
    x += temp_width + 4
    cond_width = graphics.DrawText(matrix, font, x, baseline, condition_color, condition_text)
    logging.info("DrawText condition='%s' x=%s y=%s width=%s", condition_text, x, baseline, cond_width)

    info_width = graphics.DrawText(matrix, font, 2, second_line, info_color, info_text)
    logging.info("DrawText info='%s' x=2 y=%s width=%s", info_text, second_line, info_width)

    timestamp_text = time.strftime("%H:%M:%S", time.localtime(weather.timestamp or time.time()))
    ts_width = graphics.DrawText(matrix, font, 2, third_line, info_color, f"Updated {timestamp_text}")
    logging.info("DrawText timestamp='%s' x=2 y=%s width=%s", timestamp_text, third_line, ts_width)


def draw_status(matrix: RGBMatrix, font: graphics.Font, message: str, color=None) -> None:
    matrix.Clear()
    color = color or graphics.Color(255, 165, 0)
    baseline = font.baseline
    msg = message[:32]
    width = graphics.DrawText(matrix, font, 2, baseline, color, msg)
    logging.info("DrawStatus '%s' width=%s baseline=%s", msg, width, baseline)


def weather_loop(matrix, font, service: WeatherService, args: argparse.Namespace) -> None:
    last_error = None
    frame = 0
    while True:
        frame += 1
        logging.info("Frame %s: fetching weather", frame)
        try:
            weather = service.get_latest()
            logging.info(
                "Weather: temp=%s feels=%s humidity=%s wind=%.1f condition=%s",
                weather.temp,
                weather.feels_like,
                weather.humidity,
                weather.wind_speed,
                weather.condition_main,
            )
            draw_weather(matrix, font, weather)
            last_error = None
        except WeatherProviderError as err:
            logging.error("Weather fetch failed: %s", err)
            if last_error != str(err):
                draw_status(matrix, font, "WEATHER API ERROR", graphics.Color(255, 0, 0))
            last_error = str(err)
        except Exception as exc:
            logging.exception("Unexpected error: %s", exc)
            draw_status(matrix, font, "FATAL ERROR", graphics.Color(255, 0, 0))

        time.sleep(max(args.refresh, 1.0))


def signal_handler(signum, frame):
    logging.info("Received signal %s, shutting down", signum)
    raise KeyboardInterrupt()


def main() -> None:
    args = parse_args()
    setup_logging(args.log_file, args.verbose)
    api_key, lat, lon, _ = load_config(args.units)

    matrix = init_matrix(args)
    font = load_font(args.font)
    service = build_weather_service(api_key, lat, lon, args)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    draw_status(matrix, font, "Starting weather display", graphics.Color(0, 255, 0))

    try:
        weather_loop(matrix, font, service, args)
    except KeyboardInterrupt:
        logging.info("Stopping display")
    finally:
        matrix.Clear()
        logging.info("Matrix cleared")


if __name__ == "__main__":
    main()
