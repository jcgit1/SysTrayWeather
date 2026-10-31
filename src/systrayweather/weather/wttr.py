from __future__ import annotations

import logging
from datetime import datetime

import httpx

from systrayweather.weather.models import WeatherSnapshot

log = logging.getLogger("systrayweather.wttr")

WTTR_URL = "https://wttr.in"


class WttrClient:
    def __init__(self, timeout: float = 15.0) -> None:
        self._client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": "curl/8.0"},
        )

    def close(self) -> None:
        self._client.close()

    def fetch_temperature(self, location_name: str) -> WeatherSnapshot:
        query = location_name.split(",")[0].strip()
        url = f"{WTTR_URL}/{query}?format=j1"
        log.info("WTTR.in: GET %s", url)
        resp = self._client.get(url)
        resp.raise_for_status()
        payload = resp.json()
        conditions = payload.get("current_condition") or []
        if not conditions:
            raise ValueError("WTTR.in returned no current conditions")

        temp_f = float(conditions[0]["temp_F"])
        log.info("WTTR.in: %s temp=%.1fF", query, temp_f)
        return WeatherSnapshot(
            location_name="WTTR.in",
            current_temperature=temp_f,
            updated_at=datetime.now().astimezone(),
        )
