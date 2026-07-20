from __future__ import annotations

from datetime import datetime

import httpx

from systrayweather.weather.base import GeocodingResult
from systrayweather.weather.models import WeatherSnapshot

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoClient:
    def __init__(self, timeout: float = 15.0) -> None:
        self._client = httpx.Client(timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def geocode_location(self, query: str) -> GeocodingResult:
        cleaned = query.strip()
        if not cleaned:
            raise ValueError("Location query is empty")

        attempts = [cleaned]
        if "," in cleaned:
            attempts.append(cleaned.split(",", 1)[0].strip())

        last_error: Exception | None = None
        for attempt in attempts:
            try:
                return self._geocode_search(attempt, us_only=cleaned.isdigit())
            except ValueError as exc:
                last_error = exc

        raise ValueError(f"No location found for \"{query}\"") from last_error

    def _geocode_search(self, query: str, us_only: bool = False) -> GeocodingResult:
        params: dict = {"name": query, "count": 5, "language": "en"}
        if us_only or query.isdigit():
            params["countryCode"] = "US"

        response = self._client.get(GEOCODING_URL, params=params)
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results") or []
        if not results:
            raise ValueError(f"No location found for \"{query}\"")

        place = results[0]
        name = place.get("name", query)
        admin1 = place.get("admin1")
        country = place.get("country")
        if admin1:
            location_name = f"{name}, {admin1}"
        elif country:
            location_name = f"{name}, {country}"
        else:
            location_name = name
        return GeocodingResult(
            latitude=float(place["latitude"]),
            longitude=float(place["longitude"]),
            timezone=str(place.get("timezone") or "auto"),
            location_name=location_name,
        )

    def fetch_weather(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        location_name: str,
    ) -> WeatherSnapshot:
        response = self._client.get(
            FORECAST_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "timezone": timezone or "auto",
                "current": "temperature_2m",
                "temperature_unit": "fahrenheit",
            },
        )
        response.raise_for_status()
        payload = response.json()
        current = payload.get("current") or {}
        temp = current.get("temperature_2m")
        if temp is None:
            raise ValueError("No current temperature returned from API")

        return WeatherSnapshot(
            location_name=location_name,
            current_temperature=float(temp),
            updated_at=datetime.now().astimezone(),
        )
