from __future__ import annotations

import logging
from datetime import datetime

import httpx

from systrayweather.weather.models import WeatherSnapshot

log = logging.getLogger("systrayweather.weather_gov")

POINTS_URL = "https://api.weather.gov/points"
HOURLY_URL = "https://api.weather.gov/gridpoints"
_HEADERS = {"User-Agent": "SysTrayWeather/0.1 (personal use)"}


class WeatherGovClient:
    def __init__(self, timeout: float = 15.0) -> None:
        self._client = httpx.Client(timeout=timeout, headers=_HEADERS)

    def close(self) -> None:
        self._client.close()

    def fetch_temperature(self, latitude: float, longitude: float) -> WeatherSnapshot:
        lat_rounded = round(latitude, 4)
        lon_rounded = round(longitude, 4)

        points_url = f"{POINTS_URL}/{lat_rounded},{lon_rounded}"
        log.info("Weather.gov: GET %s", points_url)
        resp = self._client.get(points_url)
        resp.raise_for_status()
        props = resp.json()["properties"]
        grid_id = props["gridId"]
        grid_x = props["gridX"]
        grid_y = props["gridY"]

        hourly_url = f"{HOURLY_URL}/{grid_id}/{grid_x},{grid_y}/forecast/hourly"
        log.info("Weather.gov: GET %s", hourly_url)
        resp = self._client.get(hourly_url)
        resp.raise_for_status()
        periods = resp.json()["properties"]["periods"]
        if not periods:
            raise ValueError("Weather.gov returned no forecast periods")

        period = periods[0]
        temp = float(period["temperature"])
        unit = period.get("temperatureUnit", "F")
        if unit == "C":
            temp = temp * 9.0 / 5.0 + 32.0

        log.info("Weather.gov: station grid=%s/%s,%s temp=%.1fF", grid_id, grid_x, grid_y, temp)
        return WeatherSnapshot(
            location_name="Weather.gov (NWS)",
            current_temperature=temp,
            updated_at=datetime.now().astimezone(),
        )
