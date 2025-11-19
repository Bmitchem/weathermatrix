"""OpenWeather Current Weather API provider implementation."""
import logging
import requests
from typing import Optional
from weather_provider import WeatherProviderBase, WeatherProviderError
from weather_data import WeatherData


class OpenWeatherProvider(WeatherProviderBase):
    """
    Weather provider using OpenWeather Current Weather API.
    
    Uses the free Current Weather API: https://openweathermap.org/current
    This API doesn't require a paid subscription like One Call API 3.0.
    """
    
    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
    
    def __init__(
        self,
        api_key: str,
        lat: float,
        lon: float,
        units: str = "metric",
        lang: str = "en",
        timeout: int = 10
    ):
        """
        Initialize OpenWeather provider.
        
        Args:
            api_key: OpenWeather API key
            lat: Latitude (-90 to 90)
            lon: Longitude (-180 to 180)
            units: Temperature units ("metric", "imperial", or "standard")
            lang: Language code for descriptions (e.g., "en", "de")
            timeout: HTTP request timeout in seconds
        """
        self.api_key = api_key
        self.lat = lat
        self.lon = lon
        self.units = units
        self.lang = lang
        self.timeout = timeout
    
    def get_current(self) -> WeatherData:
        """
        Fetch current weather from OpenWeather Current Weather API.
        
        Returns:
            WeatherData: Current weather information
            
        Raises:
            WeatherProviderError: If the API request fails
        """
        params = {
            "lat": self.lat,
            "lon": self.lon,
            "appid": self.api_key,
            "units": self.units,
            "lang": self.lang,
        }
        
        try:
            logging.info(f"Making OpenWeather API request: {self.BASE_URL}")
            logging.debug(f"Request parameters: lat={self.lat}, lon={self.lon}, units={self.units}, lang={self.lang}")
            
            response = requests.get(self.BASE_URL, params=params, timeout=self.timeout)
            
            logging.info(f"API response status: {response.status_code}")
            logging.debug(f"Response headers: {dict(response.headers)}")
            
            # Check HTTP status
            if not response.ok:
                logging.error(f"API request failed with status {response.status_code}")
                self._handle_error_response(response)
            
            data = response.json()
            logging.debug(f"API response data keys: {list(data.keys())}")
            # Log full response in debug mode (truncated for readability)
            logging.debug(f"API response (truncated): {str(data)[:500]}...")
            
            # Current Weather API returns data directly (not nested in "current")
            # Extract weather array (usually has one element)
            weather_array = data.get("weather", [])
            if not weather_array:
                logging.error("Response missing 'weather' array")
                raise WeatherProviderError("Response missing 'weather' array")
            weather = weather_array[0]
            logging.debug(f"Weather condition: {weather.get('main')} - {weather.get('description')}")
            
            # Extract main data block
            main_data = data.get("main", {})
            if not main_data:
                raise WeatherProviderError("Response missing 'main' block")
            
            # Extract precipitation (optional fields)
            rain = data.get("rain", {})
            snow = data.get("snow", {})
            precip_1h = 0.0
            has_precip = False
            
            if rain:
                precip_1h = rain.get("1h", 0.0)
                has_precip = True
            elif snow:
                precip_1h = snow.get("1h", 0.0)
                has_precip = True
            
            # Extract wind data
            wind_data = data.get("wind", {})
            wind_speed = wind_data.get("speed", 0.0) if wind_data else 0.0
            
            # Extract clouds data
            clouds_data = data.get("clouds", {})
            cloudiness = clouds_data.get("all") if clouds_data else None
            
            # Map to WeatherData
            weather_data = WeatherData(
                temp=main_data.get("temp", 0.0),
                feels_like=main_data.get("feels_like", 0.0),
                humidity=main_data.get("humidity", 0.0),
                wind_speed=wind_speed,
                condition_main=weather.get("main", "Unknown"),
                condition_description=weather.get("description", ""),
                has_precip=has_precip,
                precip_1h=precip_1h,
                timestamp=data.get("dt", 0),
                timezone_offset=data.get("timezone", 0),  # Note: Current API uses "timezone" not "timezone_offset"
                pressure=main_data.get("pressure"),
                visibility=data.get("visibility"),
                cloudiness=cloudiness,
            )
            
            logging.info(f"Successfully parsed weather data: {weather_data.temp}°C, {weather_data.condition_main}")
            return weather_data
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Network error during API request: {e}")
            raise WeatherProviderError(f"Network error: {str(e)}")
        except (KeyError, ValueError, TypeError) as e:
            logging.error(f"Failed to parse API response: {e}", exc_info=True)
            raise WeatherProviderError(f"Failed to parse response: {str(e)}")
    
    def _handle_error_response(self, response: requests.Response) -> None:
        """Parse and raise error from OpenWeather error response."""
        try:
            error_data = response.json()
            cod = error_data.get("cod", response.status_code)
            message = error_data.get("message", "Unknown error")
            parameters = error_data.get("parameters", [])
            
            logging.error(f"OpenWeather API error response: {error_data}")
            
            error_msg = f"OpenWeather API error {cod}: {message}"
            if parameters:
                error_msg += f" (parameters: {', '.join(parameters)})"
            
            raise WeatherProviderError(error_msg)
        except ValueError:
            # Not JSON, use HTTP status
            logging.error(f"Non-JSON error response: HTTP {response.status_code}, body: {response.text[:500]}")
            raise WeatherProviderError(
                f"HTTP {response.status_code}: {response.text[:200]}"
            )

