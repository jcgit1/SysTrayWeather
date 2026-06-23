from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

ZIP_PATTERN = re.compile(r"^\d{5}$")
CONFIG_DIR = Path.home() / ".config" / "systrayweather"
CONFIG_PATH = CONFIG_DIR / "config.json"


@dataclass
class AppConfig:
    location_query: str = ""
    location_name: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    timezone: str = "auto"
    units: str = "imperial"
    poll_interval_minutes: int = 10
    location_setup_complete: bool = False

    # Backward compatibility with configs that used zip_code.
    zip_code: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(
            self.location_setup_complete
            and self.latitude
            and self.longitude
            and self.location_name
        )

    @classmethod
    def load(cls) -> AppConfig:
        if not CONFIG_PATH.exists():
            return cls()
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            location_query = str(
                data.get("location_query") or data.get("zip_code") or ""
            )
            return cls(
                location_query=location_query,
                location_name=str(data.get("location_name", "")),
                latitude=float(data.get("latitude", 0.0)),
                longitude=float(data.get("longitude", 0.0)),
                timezone=str(data.get("timezone", "auto")),
                units=str(data.get("units", "imperial")),
                poll_interval_minutes=int(data.get("poll_interval_minutes", 10)),
                location_setup_complete=bool(data.get("location_setup_complete", False)),
                zip_code=str(data.get("zip_code", "")),
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            return cls()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "location_query": self.location_query,
            "location_name": self.location_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone": self.timezone,
            "units": self.units,
            "poll_interval_minutes": self.poll_interval_minutes,
            "location_setup_complete": self.location_setup_complete,
        }
        CONFIG_PATH.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )


def validate_location_query(query: str) -> str | None:
    cleaned = query.strip()
    if not cleaned:
        return "Enter a city name or 5-digit US zip code."
    if cleaned.isdigit():
        if not ZIP_PATTERN.match(cleaned):
            return "Enter a valid 5-digit US zip code."
    elif len(cleaned) < 2:
        return "Enter at least 2 characters for a city search."
    return None
