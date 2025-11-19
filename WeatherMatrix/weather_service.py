"""Weather service with caching and rate limiting."""
import logging
import time
from typing import Optional
from weather_provider import WeatherProviderBase, WeatherProviderError
from weather_data import WeatherData


class WeatherService:
    """
    Service that wraps a weather provider with caching and rate limiting.
    
    Prevents hammering the API by caching results and only fetching
    new data when the cache is stale (default: 10 minutes).
    """
    
    def __init__(
        self,
        provider: WeatherProviderBase,
        cache_ttl_seconds: int = 600,  # 10 minutes default
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0
    ):
        """
        Initialize weather service.
        
        Args:
            provider: Weather provider to use
            cache_ttl_seconds: How long to cache results before fetching new data
            max_retries: Maximum number of retries on transient errors
            retry_delay_seconds: Delay between retries
        """
        self.provider = provider
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        
        self._cached_data: Optional[WeatherData] = None
        self._cache_timestamp: float = 0.0
    
    def get_latest(self) -> WeatherData:
        """
        Get the latest weather data, using cache if still fresh.
        
        Returns:
            WeatherData: Latest weather data (may be cached)
            
        Raises:
            WeatherProviderError: If all retries fail and no cache exists
        """
        current_time = time.time()
        
        # Check if cache is still valid
        if self._cached_data is not None:
            cache_age = current_time - self._cache_timestamp
            if cache_age < self.cache_ttl_seconds:
                logging.debug(f"Using cached weather data (age: {cache_age:.1f}s, TTL: {self.cache_ttl_seconds}s)")
                return self._cached_data
            else:
                logging.info(f"Cache expired (age: {cache_age:.1f}s > TTL: {self.cache_ttl_seconds}s), fetching new data")
        
        # Cache expired or doesn't exist, fetch new data
        logging.info("Fetching weather data from provider...")
        last_error = None
        for attempt in range(self.max_retries):
            try:
                logging.debug(f"Weather fetch attempt {attempt + 1}/{self.max_retries}")
                new_data = self.provider.get_current()
                logging.info(f"Weather fetch successful: {new_data.temp}°C, {new_data.condition_main}")
                self._cached_data = new_data
                self._cache_timestamp = current_time
                return new_data
            except WeatherProviderError as e:
                last_error = e
                logging.warning(f"Weather fetch attempt {attempt + 1} failed: {e}")
                # Don't retry on 4xx errors (bad request, auth, etc.)
                if "401" in str(e) or "400" in str(e) or "404" in str(e):
                    logging.error(f"Non-retryable error (4xx), stopping retries")
                    break
                # Retry on network/5xx errors
                if attempt < self.max_retries - 1:
                    retry_delay = self.retry_delay_seconds * (attempt + 1)
                    logging.info(f"Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
        
        # All retries failed
        if self._cached_data is not None:
            # Return stale cache as fallback
            cache_age = current_time - self._cache_timestamp
            logging.warning(f"All retries failed, using stale cache (age: {cache_age:.1f}s)")
            return self._cached_data
        
        # No cache available, raise error
        logging.error(f"Failed to fetch weather after {self.max_retries} attempts, no cache available")
        raise WeatherProviderError(
            f"Failed to fetch weather after {self.max_retries} attempts: {last_error}"
        )

