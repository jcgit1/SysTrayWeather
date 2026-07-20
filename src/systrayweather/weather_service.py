from __future__ import annotations

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

from systrayweather.config import AppConfig, DEFAULT_POLL_INTERVAL_MINUTES
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
        minutes = self._config.poll_interval_minutes or DEFAULT_POLL_INTERVAL_MINUTES
        interval_ms = max(1, minutes) * 60 * 1000
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

    def close(self) -> None:
        self._timer.stop()
        if self._worker and self._worker.isRunning():
            self._worker.wait(3000)
        self._client.close()
