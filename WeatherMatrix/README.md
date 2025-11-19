# Weather Matrix Display

Display local weather data on a 64x32 RGB LED matrix using the rpi-rgb-led-matrix library.

## Features

- **Swappable weather providers**: Object-oriented design allows swapping weather APIs
- **Caching**: Prevents API rate limiting with intelligent caching
- **Testable**: Fake canvas backend for testing without hardware
- **Configurable**: Command-line and environment variable configuration

## Installation

### On Raspberry Pi

1. Install the rpi-rgb-led-matrix library (see main README)
2. Install Python dependencies:

```bash
pip install -r requirements.txt
```

### For Development/Testing (without hardware)

```bash
pip install -r requirements.txt
```

## Configuration

### Environment Variables / .env File

Create a `.env` file in the project directory (or set environment variables):

```bash
OPENWEATHER_API_KEY=your_api_key_here
WEATHER_LAT=33.44
WEATHER_LON=-94.04
WEATHER_PROVIDER=openweather
WEATHER_UNITS=metric
WEATHER_LANG=en
```

Supported variables:
- `OPENWEATHER_API_KEY`: Your OpenWeather API key (required)
- `WEATHER_LAT`: Latitude (required)
- `WEATHER_LON`: Longitude (required)
- `WEATHER_PROVIDER`: Weather provider name (default: "openweather")
- `WEATHER_UNITS`: Temperature units - "metric", "imperial", or "standard" (default: "metric")
- `WEATHER_LANG`: Language code for descriptions (default: "en")

**Note**: The `.env` file is automatically loaded if `python-dotenv` is installed. Make sure to add `.env` to `.gitignore` to avoid committing your API key.

### Command-Line Arguments

See `python main.py --help` for full list. Key options:

- `--provider`: Weather provider (default: openweather)
- `--api-key`: OpenWeather API key
- `--lat`, `--lon`: Location coordinates
- `--units`: Temperature units
- `--backend`: "pi" for real hardware, "fake" for testing
- `--font`: Path to BDF font file
- `--led-rows`, `--led-cols`: Matrix dimensions (default: 32x64)
- All standard rpi-rgb-led-matrix flags (--led-chain, --led-brightness, etc.)

## Usage

### On Raspberry Pi (with hardware)

```bash
sudo python3 main.py \
  --api-key YOUR_API_KEY \
  --lat 33.44 \
  --lon -94.04 \
  --led-rows 32 \
  --led-cols 64 \
  --font ../rpi-rgb-led-matrix-master/fonts/7x13.bdf
```

### For Testing (without hardware)

```bash
python3 main.py \
  --backend fake \
  --api-key YOUR_API_KEY \
  --lat 33.44 \
  --lon -94.04
```

This will print ASCII art representation of the display.

## Testing

Run tests:

```bash
pytest
```

Tests include:
- Unit tests for weather data models
- Mocked HTTP tests for OpenWeather provider
- Cache and retry logic tests for WeatherService
- Layout calculation tests
- Fake canvas tests

## Architecture

### Weather Provider Abstraction

The code uses an object-oriented design to allow swapping weather providers:

- `WeatherProviderBase`: Abstract interface
- `OpenWeatherProvider`: OpenWeather One Call API 3.0 implementation
- `WeatherService`: Wraps provider with caching and rate limiting

To add a new provider, implement `WeatherProviderBase` and update `main.py` to instantiate it.

### Matrix Canvas Abstraction

- `MatrixCanvas`: Abstract interface
- `RealMatrixCanvas`: Uses actual RGB matrix hardware
- `FakeMatrixCanvas`: In-memory implementation for testing

This allows testing rendering logic without hardware.

### Layout System

- `layout.py`: Pure functions for calculating what to draw
- `calculate_layout()`: Returns list of drawing operations (testable)
- `render_weather()`: Executes drawing operations on canvas

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest test_openweather_provider.py
```

### Testing Without Hardware

Use `--backend=fake` to run the application without hardware. The fake canvas will print ASCII art to stdout.

## License

This code is provided as-is. The rpi-rgb-led-matrix library is GPL v2.

