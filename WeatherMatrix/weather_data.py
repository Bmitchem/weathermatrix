"""Weather domain model - pure data structures independent of any API."""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class WeatherData:
    """Domain model for weather data, independent of any specific API."""
    temp: float
    feels_like: float
    humidity: float
    wind_speed: float
    condition_main: str  # e.g., "Clouds", "Rain", "Clear"
    condition_description: str  # e.g., "broken clouds", "light rain"
    has_precip: bool
    precip_1h: float  # mm of precipitation in last hour (0 if none)
    timestamp: int  # UNIX timestamp (UTC)
    timezone_offset: int  # Offset from UTC in seconds
    
    # Optional fields that might be useful
    pressure: Optional[float] = None
    visibility: Optional[int] = None
    cloudiness: Optional[int] = None  # percentage
    
    def is_stale(self, max_age_seconds: int = 900) -> bool:
        """Check if this data is stale (older than max_age_seconds)."""
        current_time = int(datetime.utcnow().timestamp())
        age = current_time - self.timestamp
        return age > max_age_seconds

