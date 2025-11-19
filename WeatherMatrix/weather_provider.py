"""Weather provider abstraction - allows swapping different weather APIs."""
from abc import ABC, abstractmethod
from weather_data import WeatherData


class WeatherProviderBase(ABC):
    """Abstract base class for weather data providers."""
    
    @abstractmethod
    def get_current(self) -> WeatherData:
        """
        Fetch current weather data.
        
        Returns:
            WeatherData: Current weather information
            
        Raises:
            WeatherProviderError: If the provider fails to fetch data
        """
        pass


class WeatherProviderError(Exception):
    """Exception raised when a weather provider fails."""
    pass

