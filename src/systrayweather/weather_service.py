from __future__ import annotations

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

from systrayweather.config import AppConfig
from systrayweather.weather.models import WeatherSnapshot
from systrayweather.weather.open_meteo import OpenMeteoClient


class FetchWorker(QThread):
    finished = pyqtSignal(object, object)

    def __init__(self, client: OpenMeteoClient, config: AppConfig) -> None:
        super().__init__()
        self._client = client
        self._config = config

    def run(self) -> None:
        try:
            snapshot = self._client.fetch_weather(
                self._config.latitude,
                self._config.longitude,
                self._config.timezone,
                self._config.location_name,
            )
            self.finished.emit(snapshot, None)
        except Exception as exc:
            self.finished.emit(None, str(exc))


class WeatherService(QObject):
    weather_updated = pyqtSignal(object, object)

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self._config = config
        self._client = OpenMeteoClient()
        self._cache: WeatherSnapshot | None = None
        self._worker: FetchWorker | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)

    @property
    def cache(self) -> WeatherSnapshot | None:
        return self._cache

    def start(self) -> None:
        interval_ms = max(1, self._config.poll_interval_minutes) * 60 * 1000
        self._timer.start(interval_ms)
        self.refresh()

    def refresh(self) -> None:
        if self._worker and self._worker.isRunning():
            return
        self._worker = FetchWorker(self._client, self._config)
        self._worker.finished.connect(self._on_fetch_finished)
        self._worker.start()

    def _on_fetch_finished(self, snapshot: WeatherSnapshot | None, error: str | None) -> None:
        if snapshot:
            self._cache = snapshot
        self.weather_updated.emit(self._cache, error)

    def geocode_and_save(self, location_query: str) -> None:
        result = self._client.geocode_location(location_query)
        self._config.location_query = location_query
        self._config.latitude = result.latitude
        self._config.longitude = result.longitude
        self._config.timezone = result.timezone
        self._config.location_name = result.location_name
        self._config.location_setup_complete = True
        self._config.save()

    def close(self) -> None:
        self._timer.stop()
        if self._worker and self._worker.isRunning():
            self._worker.wait(3000)
        self._client.close()
