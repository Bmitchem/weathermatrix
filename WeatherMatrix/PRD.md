# Weather Matrix Display PRD (v1.0)

## 1. Overview
- **Goal**: Render current Baltimore weather on a 128x32 RGB LED.
- **Primary Users**: Single owner/operator tinkering with Raspberry Pi signage.

## 2. Functional Requirements
1. **Weather Data**
   - Use OpenWeather Current Weather API with lat/lon from `.env`.
   - Data model (`WeatherData`): temp, feels_like, humidity, wind_speed, condition_main/description, precip flags, timestamp, timezone_offset.
   - Cache weather calls for `cache_ttl` (default 600s) with retries/backoff.
2. **Display Rendering**
   - Metro-style script drives matrix directly (no abstractions) with `graphics.DrawText`.
   - Default layout: top row temp + condition, second row status (feels, humidity, wind), third row “Updated HH:MM:SS”.
   - Backends: `pi` (hardware), `png` (PIL), `fake` (ASCII).
   - Font defaults to `fonts/6x10.bdf`; CLI flag `--font` overrides.
3. **Startup + Diagnostics**
   - CLI flag `--verbose` enables debug logging.
   - Logging lines for every DrawText call with x/y/width.
   - `hardware_diag.py` exercises fill, grid, and text.
4. **Configuration**
   - `.env`: `WEATHER_API_KEY`, `WEATHER_LAT`, `WEATHER_LON`, optional `WEATHER_LANG`.
   - CLI toggles: LED geometry, brightness, refresh cadence, caching params.
