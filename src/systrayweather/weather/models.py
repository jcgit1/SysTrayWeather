from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class HourForecast:
    time: datetime
    temperature: float
    precipitation_probability: float | None
    weather_code: int


@dataclass(frozen=True)
class DayForecast:
    day: date
    label: str
    high: float
    low: float
    precipitation_probability: float | None
    weather_code: int

    @property
    def rainy(self) -> bool:
        return self.precipitation_probability is not None and self.precipitation_probability > 30


@dataclass(frozen=True)
class WeatherSnapshot:
    location_name: str
    current_temperature: float
    current_weather_code: int
    updated_at: datetime
    yesterday: DayForecast | None
    today: DayForecast
    tomorrow: DayForecast
    hourly: list[HourForecast]
    daily: list[DayForecast]
    weekly: list[DayForecast]
