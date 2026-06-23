from __future__ import annotations

from datetime import date, datetime, timedelta

import httpx

from systrayweather.weather.base import GeocodingResult
from systrayweather.weather.models import DayForecast, HourForecast, WeatherSnapshot

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

    def geocode_zip(self, zip_code: str) -> GeocodingResult:
        return self.geocode_location(zip_code)

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
                "past_days": 1,
                "forecast_days": 16,
                "current": "temperature_2m,weather_code",
                "hourly": "temperature_2m,precipitation_probability,weather_code",
                "daily": (
                    "temperature_2m_max,temperature_2m_min,"
                    "precipitation_probability_max,weather_code"
                ),
                "temperature_unit": "fahrenheit",
                "precipitation_unit": "inch",
                "wind_speed_unit": "mph",
            },
        )
        response.raise_for_status()
        payload = response.json()
        return _parse_snapshot(payload, location_name)


def _parse_snapshot(payload: dict, location_name: str) -> WeatherSnapshot:
    current = payload.get("current") or {}
    daily = payload.get("daily") or {}
    hourly = payload.get("hourly") or {}

    daily_times = daily.get("time") or []
    daily_highs = daily.get("temperature_2m_max") or []
    daily_lows = daily.get("temperature_2m_min") or []
    daily_precip = daily.get("precipitation_probability_max") or []
    daily_codes = daily.get("weather_code") or []

    daily_forecasts: list[DayForecast] = []
    for i, day_str in enumerate(daily_times):
        high = _optional_float(daily_highs, i)
        low = _optional_float(daily_lows, i)
        code = _optional_int(daily_codes, i)
        if high is None or low is None or code is None:
            continue
        day = date.fromisoformat(day_str)
        daily_forecasts.append(
            DayForecast(
                day=day,
                label=_day_label(day),
                high=high,
                low=low,
                precipitation_probability=_optional_float(daily_precip, i),
                weather_code=code,
            )
        )

    if not daily_forecasts:
        raise ValueError("No complete daily forecast data returned from API")

    hourly_times = hourly.get("time") or []
    hourly_temps = hourly.get("temperature_2m") or []
    hourly_precip = hourly.get("precipitation_probability") or []
    hourly_codes = hourly.get("weather_code") or []

    now = datetime.now().astimezone()
    hourly_forecasts: list[HourForecast] = []
    for i, time_str in enumerate(hourly_times):
        temp = _optional_float(hourly_temps, i)
        code = _optional_int(hourly_codes, i)
        if temp is None or code is None:
            continue
        hour_time = datetime.fromisoformat(time_str).replace(tzinfo=now.tzinfo)
        if hour_time < now - timedelta(minutes=30):
            continue
        hourly_forecasts.append(
            HourForecast(
                time=hour_time,
                temperature=temp,
                precipitation_probability=_optional_float(hourly_precip, i),
                weather_code=code,
            )
        )
        if len(hourly_forecasts) >= 12:
            break

    yesterday = daily_forecasts[0] if len(daily_forecasts) > 0 else None
    today = daily_forecasts[1] if len(daily_forecasts) > 1 else daily_forecasts[0]
    tomorrow = daily_forecasts[2] if len(daily_forecasts) > 2 else today

    return WeatherSnapshot(
        location_name=location_name,
        current_temperature=float(current.get("temperature_2m", 0)),
        current_weather_code=int(current.get("weather_code", 0)),
        updated_at=datetime.now().astimezone(),
        yesterday=yesterday,
        today=today,
        tomorrow=tomorrow,
        hourly=hourly_forecasts,
        daily=daily_forecasts[1:13] if len(daily_forecasts) > 1 else daily_forecasts,
        weekly=daily_forecasts[1:15] if len(daily_forecasts) > 1 else daily_forecasts,
    )


def _optional_float(values: list, index: int) -> float | None:
    if index >= len(values):
        return None
    value = values[index]
    if value is None:
        return None
    return float(value)


def _optional_int(values: list, index: int) -> int | None:
    if index >= len(values):
        return None
    value = values[index]
    if value is None:
        return None
    return int(value)


def _day_label(day: date) -> str:
    today = date.today()
    if day == today:
        return "Today"
    if day == today - timedelta(days=1):
        return "Yesterday"
    if day == today + timedelta(days=1):
        return "Tomorrow"
    return day.strftime("%a %b %d")
