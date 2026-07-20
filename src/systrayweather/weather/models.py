from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class WeatherSnapshot:
    location_name: str
    current_temperature: float
    updated_at: datetime
