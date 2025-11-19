"""OpenWeather Current Weather API provider implementation."""
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
            response = requests.get(self.BASE_URL, params=params, timeout=self.timeout)
            
            # Check HTTP status
            if not response.ok:
                self._handle_error_response(response)
            
            data = response.json()
            
            # Current Weather API returns data directly (not nested in "current")
            # Extract weather array (usually has one element)
            weather_array = data.get("weather", [])
            if not weather_array:
                raise WeatherProviderError("Response missing 'weather' array")
            weather = weather_array[0]
            
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
            return WeatherData(
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
            
        except requests.exceptions.RequestException as e:
            raise WeatherProviderError(f"Network error: {str(e)}")
        except (KeyError, ValueError, TypeError) as e:
            raise WeatherProviderError(f"Failed to parse response: {str(e)}")
    
    def _handle_error_response(self, response: requests.Response) -> None:
        """Parse and raise error from OpenWeather error response."""
        try:
            error_data = response.json()
            cod = error_data.get("cod", response.status_code)
            message = error_data.get("message", "Unknown error")
            parameters = error_data.get("parameters", [])
            
            error_msg = f"OpenWeather API error {cod}: {message}"
            if parameters:
                error_msg += f" (parameters: {', '.join(parameters)})"
            
            raise WeatherProviderError(error_msg)
        except ValueError:
            # Not JSON, use HTTP status
            raise WeatherProviderError(
                f"HTTP {response.status_code}: {response.text[:200]}"
            )

