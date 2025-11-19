## OpenWeather One Call API 3.0 – Practical Implementation Guide

If you can’t build a client from this, that’s on you. This document explains how to use OpenWeather’s **One Call API 3.0** end‑to‑end: get access, call it, understand responses, and handle errors, based on their official docs [`https://openweathermap.org/api/one-call-3`](https://openweathermap.org/api/one-call-3).

---

## 1. What One Call API 3.0 Actually Is

- **Purpose**: Single API family that gives you:
  - **Current weather**
  - **Minutely forecast** for 1 hour
  - **Hourly forecast** for 48 hours
  - **Daily forecast** for 8 days
  - **Government weather alerts**
  - **Historical + future timestamped data** (46+ years history, 4 days ahead)
  - **Daily aggregations** (46+ years back, ~1.5 years forward)
  - **Weather overview + AI assistant outputs**
- **Design goal**: Easy migration from Dark Sky; one coordinate pair in, all the weather out.
- **Update frequency**: Internal model is updated about **every 10 minutes**. If you query more frequently, that’s mostly on you (and your bill).

Core reference: [`https://openweathermap.org/api/one-call-3`](https://openweathermap.org/api/one-call-3)

---

## 2. Access & Accounts (Before You Touch Code)

- **Step 1 – Sign up**
  - Go to OpenWeather and create an account (free or paid).
  - You get an API key under your account’s **“API keys”** tab.
- **Step 2 – Subscribe to the correct product**
  - One Call API 3.0 is part of **“One Call by Call”** subscription.
  - You do **not** need other OpenWeather subscriptions for this.
  - The subscription includes **1,000 free API calls per day** for One Call 3.0; the default daily cap is **2,000 calls/day**, which you can adjust in the **“Billing plans”** tab in your account.
- **Step 3 – Get your API key (`appid`)**
  - Copy it from your account page (`API key` tab).
  - This key must be sent as `appid=YOUR_KEY` in **every** request.
- **Step 4 – Understand billing**
  - You pay **per API call** to this product.
  - Exceeding the free daily quota will cost money; hitting hard rate limits will get you `429 Too Many Requests`.

> **If you're still on One Call 2.5**: OpenWeather discontinued **One Call API 2.5** in **June 2024**. New code must target **One Call API 3.0**; migrate immediately if you haven't already.

If you skip this section and complain about `401 Unauthorized`, that’s not the API’s fault.

---

## 3. Core Endpoint: Current + Forecasts

### 3.1 URL Format

Base endpoint for **current & forecast weather**:

```text
https://api.openweathermap.org/data/3.0/onecall
```

### 3.2 Required Query Parameters

- **`lat`** (required):
  - Latitude in decimal degrees, range \(-90 .. 90\).
  - Example: `lat=33.44`
- **`lon`** (required):
  - Longitude in decimal degrees, range \(-180 .. 180\).
  - Example: `lon=-94.04`
- **`appid`** (required):
  - Your API key.
  - Example: `appid=YOUR_API_KEY_HERE`

If you don’t know lat/lon, use OpenWeather’s **Geocoding API** first (separate product) to convert from city/ZIP to coordinates.

### 3.3 Optional Query Parameters

- **`exclude`** (optional):
  - Comma‑separated list of blocks you **don’t** want back.
  - Allowed parts: `current`, `minutely`, `hourly`, `daily`, `alerts`
  - Example:
    - `exclude=hourly,daily` → you’ll get everything *except* those blocks.
    - `exclude=current,minutely,alerts` → only hourly + daily.
- **`units`** (optional):
  - Controls temperature and wind units:
    - `standard` (default): temperature in Kelvin
    - `metric`: Celsius (`°C`), wind speed m/s
    - `imperial`: Fahrenheit (`°F`), wind speed miles/hour
  - Example: `units=metric`
- **`lang`** (optional):
  - Localizes description text, e.g. `"broken clouds"` into another language.
  - Example: `lang=de` for German.

### 3.4 Example Calls

- **Full data (no exclusions)**:

```text
https://api.openweathermap.org/data/3.0/onecall?lat=33.44&lon=-94.04&appid=YOUR_API_KEY
```

- **Exclude hourly & daily**:

```text
https://api.openweathermap.org/data/3.0/onecall?lat=33.44&lon=-94.04&exclude=hourly,daily&appid=YOUR_API_KEY
```

- **Metric units, German descriptions, only hourly & daily**:

```text
https://api.openweathermap.org/data/3.0/onecall?lat=33.44&lon=-94.04&exclude=current,minutely,alerts&units=metric&lang=de&appid=YOUR_API_KEY
```

---

## 4. Response Structure – What You Actually Get

The One Call response is a big JSON object. Major top‑level fields:

- **`lat`** / **`lon`**:
  - The coordinates you requested (may be normalized).
- **`timezone`**:
  - Timezone name, e.g. `"America/Chicago"`.
- **`timezone_offset`**:
  - Offset from UTC in seconds, e.g. `-18000` for UTC‑5.
- **`current`**:
  - Current weather snapshot.
- **`minutely`**:
  - Minute‑by‑minute forecast for 60 minutes.
- **`hourly`**:
  - Hourly forecast for 48 hours.
- **`daily`**:
  - Daily forecast for 8 days.
- **`alerts`**:
  - Government weather alerts, if available.

If you used `exclude`, some of these will be missing. Your code should not act surprised.

### 4.1 `current` Object

Typical structure (simplified from docs):

```json
{
  "dt": 1684929490,
  "sunrise": 1684926645,
  "sunset": 1684977332,
  "temp": 292.55,
  "feels_like": 292.87,
  "pressure": 1014,
  "humidity": 89,
  "dew_point": 290.69,
  "uvi": 0.16,
  "clouds": 53,
  "visibility": 10000,
  "wind_speed": 3.13,
  "wind_deg": 93,
  "wind_gust": 6.71,
  "weather": [
    {
      "id": 803,
      "main": "Clouds",
      "description": "broken clouds",
      "icon": "04d"
    }
  ],
  "rain": { "1h": 2.93 },   // present only if raining
  "snow": { "1h": 1.2 }     // present only if snowing
}
```

- **Key points**:
  - `dt`, `sunrise`, `sunset` are UNIX timestamps (UTC).
  - `weather` is an **array**, but usually has **one** element.
  - Use `weather[0].id` and `weather[0].description` when you just need the main condition.
  - `rain` and `snow` are optional.

### 4.2 `minutely` Array

- **Type**: array of objects (up to 60 entries).
- Each item:

```json
{
  "dt": 1684929540,
  "precipitation": 0
}
```

- `precipitation` is in mm of liquid water.
- Time granularity: 1 minute steps from current time.

### 4.3 `hourly` Array

- **Type**: array of objects (up to 48 entries).
- Each object includes fields similar to `current`, plus:
  - `pop` = probability of precipitation (0.0 – 1.0).

Simplified example:

```json
{
  "dt": 1684926000,
  "temp": 292.01,
  "feels_like": 292.33,
  "pressure": 1014,
  "humidity": 91,
  "dew_point": 290.51,
  "uvi": 0,
  "clouds": 54,
  "visibility": 10000,
  "wind_speed": 2.58,
  "wind_deg": 86,
  "wind_gust": 5.88,
  "weather": [
    {
      "id": 803,
      "main": "Clouds",
      "description": "broken clouds",
      "icon": "04n"
    }
  ],
  "pop": 0.15,
  "rain": { "1h": 2.46 }   // optional
}
```

### 4.4 `daily` Array

- **Type**: array with up to 8 daily entries.
- Each day combines many details:

```json
{
  "dt": 1595268000,
  "sunrise": 1595243663,
  "sunset": 1595296278,
  "temp": {
    "day": 298.82,
    "min": 293.25,
    "max": 301.9,
    "night": 293.25,
    "eve": 299.72,
    "morn": 293.48
  },
  "feels_like": {
    "day": 300.06,
    "night": 292.46,
    "eve": 300.87,
    "morn": 293.75
  },
  "pressure": 1014,
  "humidity": 82,
  "dew_point": 295.52,
  "wind_speed": 5.22,
  "wind_deg": 146,
  "weather": [
    {
      "id": 502,
      "main": "Rain",
      "description": "heavy intensity rain",
      "icon": "10d"
    }
  ],
  "clouds": 97,
  "pop": 1,
  "rain": 12.57,
  "uvi": 10.64
}
```

- **Implementation hint**:
  - For daily summaries, pull:
    - `temp.max`, `temp.min`
    - `weather[0].description`
    - `pop`, `rain` (if present)

### 4.5 `alerts` Array

- Contains **government-issued alerts**, if any, from a long list of agencies.

Example:

```json
{
  "sender_name": "NWS Tulsa (Eastern Oklahoma)",
  "event": "Heat Advisory",
  "start": 1597341600,
  "end": 1597366800,
  "description": "... text of the alert ..."
}
```

- Alerts are optional. Do not assume `alerts` exists.
- Useful for severe weather notifications and warnings.

---

## 5. Other One Call 3.0 Capabilities

The same product (`One Call API 3.0`) provides **multiple endpoints** beyond the main `/onecall`:

- **Weather data for timestamp**:
  - Access historical data (46+ years back) and 4 days ahead for specific timestamps.
  - Good for “what was the weather on X date?” or short‑range time series.
- **Daily aggregation**:
  - Pre‑aggregated daily data for 46+ years back and ~1.5 years ahead.
  - Saves you from manually aggregating hourly data.
- **Weather overview**:
  - Human‑readable summaries for today + tomorrow using OpenWeather’s AI.
- **AI Weather Assistant**:
  - Chatty interface that returns weather data and advice in human language.

All of these live under the same **One Call API 3.0** umbrella and share the same subscription / key model. Details are on the same docs page: [`https://openweathermap.org/api/one-call-3`](https://openweathermap.org/api/one-call-3).

For an intern: start with the main `/onecall` endpoint first; only touch the others once you’ve proved you can successfully parse JSON without crying.

---

## 6. JSONP / `callback` (Docs vs. Reality)

The current **One Call API 3.0** documentation does **not** list JSONP or a `callback` query parameter for the `/onecall` endpoint.

- Older OpenWeather examples (for other endpoints / generations) used JSONP like:

```text
https://api.openweathermap.org/data/3.0/onecall?lat=38.8&lon=12.09&callback=test&appid=YOUR_API_KEY
```

  …returning something like:

```text
test({ ...normal JSON payload... })
```

- That pattern is **not documented** for One Call 3.0. Assume it is **unsupported** and do **not** build new code that depends on JSONP here.
- If you’re whining about CORS, fix it properly: use standard JSON over HTTPS and handle CORS on the backend or via a proxy instead of clinging to JSONP.

---

## 7. Error Handling – What Will Break and How

Error responses are JSON too, with this shape:

```json
{
  "cod": 400,
  "message": "Invalid date format",
  "parameters": ["date"]
}
```

- **Fields**:
  - `cod`: numeric HTTP‑style error code.
  - `message`: short explanation.
  - `parameters` (optional): list of parameters causing the issue.

### 7.1 Common Error Codes

- **400 – Bad Request**
  - Cause: Missing required parameters, invalid values, out‑of‑range inputs.
  - Fix: Check the `parameters` array, fix your request, **then** retry.
- **401 – Unauthorized**
  - Cause: Missing, invalid, or unauthorized `appid` key.
  - Fix: Use a valid key with permission for One Call 3.0, send it as `appid`.
- **404 – Not Found**
  - Cause: Data doesn’t exist for the given parameters (`lat`, `lon`, `date`, etc).
  - Fix: Do **not** blindly retry the same exact request. Either adjust parameters or handle as “no data”.
- **429 – Too Many Requests**
  - Cause: You exceeded allowed quota for the key.
  - Fix: Back off, wait, or pay more. Implement exponential backoff or caching.
- **5xx – Server Errors**
  - Cause: Internal OpenWeather errors.
  - Fix: You may retry after a short delay. If persistent, contact OpenWeather with example requests.

**Implementation requirement**: Always check HTTP status and handle non‑2xx codes instead of assuming everything is fine until JSON parsing explodes.

---

## 8. Usage Patterns & Best Practices

### 8.1 Call Frequency

- The model is updated about **every 10 minutes**.
- Calling it every few seconds is:
  - Useless for data freshness.
  - Great for wasting quota and hitting `429`.
- For a typical app:
  - Cache results per location for **10+ minutes**.
  - Only refresh when needed (user opens the app, explicit refresh, etc.).

### 8.2 Units and Localization

- Pick **one** unit system and stick to it in your UI.
- Always specify `units` explicitly so your app doesn’t break if default behavior changes.
- Use `lang` so textual descriptions (`description` in `weather`) match the user’s language.

### 8.3 Time Handling

- All timestamps (`dt`, `sunrise`, `sunset`, etc.) are **UNIX UTC seconds**.
- Use `timezone` and `timezone_offset` to convert times to local time.
- On clients:
  - Convert `dt + timezone_offset` to a local `DateTime`.

### 8.4 Optional Fields

- Many fields are **optional** and only present under certain conditions:
  - `rain`, `snow`, `alerts`, etc.
- Before accessing:
  - Check for existence (`if (data.rain)`).
  - Handle empty arrays (`alerts` can be missing or empty).

---

## 9. Minimal Implementation Outline (Language-Agnostic)

An intern‑level implementation should at least follow this order:

1. **Store configuration**:
   - `OPENWEATHER_API_KEY`
   - Default `lat`, `lon`
   - Preferred `units`, `lang`
2. **Build a URL**:
   - Base: `https://api.openweathermap.org/data/3.0/onecall`
   - Query params: `lat`, `lon`, `appid`, `units`, `lang`, `exclude` (if needed).
3. **Make an HTTP GET request**:
   - Use a standard HTTP client (curl, requests, fetch, etc).
   - Timeout and retry on network failures, but be smart about API errors.
4. **Check HTTP status code**:
   - 2xx → parse JSON.
   - Non‑2xx → parse error JSON and log `cod`, `message`, `parameters`.
5. **Parse JSON payload**:
   - Extract:
     - From `current`: `temp`, `feels_like`, `weather[0].description`, `wind_speed`, `humidity`.
     - From `hourly`: upcoming hours’ `dt`, `temp`, `pop`.
     - From `daily`: `dt`, `temp.min`, `temp.max`, `weather[0].description`.
     - From `alerts`: `event`, `start`, `end`, `description` if present.
6. **Convert timestamps**:
   - Use `timezone_offset` to convert `dt` to local time.
7. **Display or store results**:
   - Normalize to your own data structures.
   - Don’t pass raw API JSON all over your codebase unless you enjoy brittle chaos.
8. **Cache results**:
   - Cache by `(lat, lon, units, lang)` key.
   - Define a sensible TTL (e.g. 10–15 minutes).

If you do all of that and the app still doesn’t work, the bug is almost certainly in your code, not in the endpoint.

---

## 10. Quick Example Snippets

These are intentionally simple. Replace placeholders with real values.

### 10.1 `curl`

```bash
curl "https://api.openweathermap.org/data/3.0/onecall?lat=33.44&lon=-94.04&units=metric&appid=YOUR_API_KEY"
```

### 10.2 Python (requests)

```python
import os
import requests

API_KEY = os.environ.get("OPENWEATHER_API_KEY")
BASE_URL = "https://api.openweathermap.org/data/3.0/onecall"

params = {
    "lat": 33.44,
    "lon": -94.04,
    "units": "metric",
    "appid": API_KEY,
}

resp = requests.get(BASE_URL, params=params, timeout=10)
resp.raise_for_status()  # raises for 4xx/5xx
data = resp.json()

current = data.get("current", {})
weather = current.get("weather", [{}])[0]

print("Temp:", current.get("temp"))
print("Feels like:", current.get("feels_like"))
print("Conditions:", weather.get("description"))
```

### 10.3 JavaScript (Node.js `fetch`)

```javascript
const API_KEY = process.env.OPENWEATHER_API_KEY;
const url = new URL("https://api.openweathermap.org/data/3.0/onecall");
url.searchParams.set("lat", "33.44");
url.searchParams.set("lon", "-94.04");
url.searchParams.set("units", "metric");
url.searchParams.set("appid", API_KEY);

async function fetchWeather() {
  const res = await fetch(url, { method: "GET" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(`OpenWeather error ${res.status}: ${JSON.stringify(err)}`);
  }
  const data = await res.json();
  const current = data.current || {};
  const weather = (current.weather && current.weather[0]) || {};
  console.log("Temp:", current.temp);
  console.log("Conditions:", weather.description);
}

fetchWeather().catch(err => {
  console.error("Request failed:", err.message);
});
```

---

## 11. Final Notes

- Full official documentation lives here: [`https://openweathermap.org/api/one-call-3`](https://openweathermap.org/api/one-call-3).
- When in doubt:
  - Inspect the raw JSON.
  - Compare with their example payloads.
  - Fix your assumptions instead of guessing.

If you’re an intern reading this, you now have more guidance than most production systems ever get. Use it.


