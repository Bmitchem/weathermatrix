### Weather Matrix Weather Display (Python + OpenWeather)

```markdown
# Weather Matrix Weather Display (Python + OpenWeather)

### 1. Stack and architecture

- Implement the app in **Python**, using the library’s `bindings/python` API to drive the RGB matrix.
- Define a small **domain model** (`WeatherData`) and a **provider interface** (`WeatherProviderBase`) so the matrix code depends only on these, not on OpenWeather specifics.

### 2. Python bindings and matrix usage

- Review `bindings/python/README.md` and sample scripts to see how they:
  - initialize the matrix (including `--led-rows=32 --led-cols=64` and other flags),
  - draw pixels/text (font loading, colors),
  - and optionally use double-buffering.
- Create a Python module (e.g. `matrix_display.py`) that:
  - parses standard LED flags from `sys.argv` (mirroring the C++ examples),
  - initializes the matrix object,
  - knows how to render a `WeatherData` onto a 64x32 panel (text-only or text+icons).

### 3. Weather domain & provider abstraction

- Define a `WeatherData` class/`dataclass` with fields like: `temp`, `feels_like`, `humidity`, `wind_speed`, `condition_main`, `condition_description`, `has_precip`, `precip_1h`, `timestamp`, `timezone_offset`.
- Define an abstract `WeatherProviderBase` class with a single method (e.g. `get_current(self) -> WeatherData`).
- The matrix rendering code and main loop only depend on `WeatherProviderBase` and `WeatherData` so swapping providers later is trivial.

### 4. OpenWeather provider implementation

- Implement `OpenWeatherProvider(WeatherProviderBase)` that:
  - holds config: API key, lat, lon, units, lang, optional `exclude` string.
  - builds the One Call 3.0 URL: `https://api.openweathermap.org/data/3.0/onecall` with `lat`, `lon`, `appid`, `units`, `lang`, and `exclude=minutely,hourly,daily,alerts` (to focus on `current`).
  - performs an HTTP GET using a library like `requests` with a sane timeout.
  - checks HTTP status; on non-2xx, parses the error JSON (`cod`, `message`, `parameters`) and raises a clear exception.
  - parses the `current` block from the JSON as documented in `openWeatherMapReadme.md` (fields like `temp`, `feels_like`, `humidity`, `wind_speed`, `weather[0].main`, `weather[0].description`, optional `rain["1h"]` / `snow["1h"]`, `dt`, `timezone_offset`).
  - maps that into a `WeatherData` instance and returns it.
- Keep this module strictly about HTTP + JSON + mapping; no matrix logic.

### 5. Caching, rate limits, and a thin WeatherService

- Implement a `WeatherService` that wraps a `WeatherProviderBase` and handles:
  - calling `get_current()` **at most every 10–15 minutes** (aligned with OpenWeather’s update frequency),
  - caching the last successful `WeatherData` and timestamp,
  - basic retry/backoff on transient HTTP errors,
  - returning the cached data when the provider fails (optionally marking it as stale via a field in `WeatherData`).
- This keeps the render loop fast and prevents hammering the API.

### 6. 64x32 layout and rendering

- Choose a compact layout that fits 64x32:
  - e.g. line 1: `TEMP°` plus optional feels-like or unit indicator,
  - line 2: short condition text (`Cloudy`, `Rain`, `Clear`), optionally with a minimal icon.
- Select fonts from `fonts/` (e.g. `7x13.bdf` or `8x13.bdf`) and test readability on actual hardware.
- Implement a render function that:
  - clears the canvas,
  - draws the temperature in a color chosen from a simple gradient (cold = blue, warm = yellow/orange, hot = red),
  - draws condition text in a neutral or contrasting color,
  - uses double-buffering for flicker-free updates (depending on what the Python bindings expose for frame canvases / vsync swaps).

### 7. Main loop and process behavior

- Write a `main.py` that:
  - reads configuration (API key, lat/lon, units, language, refresh interval, brightness, provider name) from environment variables and/or command-line,
  - constructs an `OpenWeatherProvider` instance and wraps it in `WeatherService`,
  - parses LED matrix flags from command-line and initializes the matrix (mirroring the examples),
  - enters a loop that:
    - asks `WeatherService` for the latest `WeatherData`,
    - renders it on the matrix,
    - sleeps a short amount between frames while only fetching new data when the cache is stale.
- Add signal handling (SIGINT/SIGTERM) so Ctrl+C or service stop cleans up the matrix and exits cleanly.

### 8. Configuration and future provider swaps

- Centralize configuration (env vars and/or a simple config file) so that switching providers later is just:
  - implementing another `WeatherProviderBase` subclass,
  - changing one config value to instantiate the alternate provider.
- Keep all OpenWeather-specific constants and URLs isolated in the `OpenWeatherProvider` module to avoid leakage into the rest of the codebase.

### 9. Testing strategy

- Unit-test `OpenWeatherProvider` and `WeatherService`:
  - mock HTTP responses for success, 4xx/5xx, and malformed payloads,
  - verify correct mapping into `WeatherData` and correct caching / backoff behavior.
- For rendering, keep layout calculations (positions, colors, chosen text strings) in testable pure functions and write tests against those.
- Add a thin integration test or manual script that hits the real API under a separate flag, so normal test runs stay offline.

### 10. Hardware verification and tuning

- Before running the weather app, verify the panel and wiring with the stock Python samples or `examples-api-use` binaries (demo, clock) using `--led-rows=32 --led-cols=64` and any required mapping flags.
- Once the app runs:
  - tune `--led-brightness`, slowdown, and mapping options for stable, readable output,
  - tweak font sizes, positions, and color thresholds for your actual viewing distance.
```