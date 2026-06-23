from __future__ import annotations

from typing import Protocol

from systrayweather.weather.models import WeatherSnapshot


class GeocodingResult:
    def __init__(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        location_name: str,
    ) -> None:
        self.latitude = latitude
        self.longitude = longitude
        self.timezone = timezone
        self.location_name = location_name


class WeatherProvider(Protocol):
    def geocode_location(self, query: str) -> GeocodingResult: ...

    def fetch_weather(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        location_name: str,
    ) -> WeatherSnapshot: ...
