from __future__ import annotations

import logging
from dataclasses import dataclass, field

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal

from systrayweather.config import AppConfig, DEFAULT_POLL_INTERVAL_MINUTES
from systrayweather.weather.models import WeatherSnapshot
from systrayweather.weather.open_meteo import OpenMeteoClient
from systrayweather.weather.weather_gov import WeatherGovClient
from systrayweather.weather.wttr import WttrClient

log = logging.getLogger("systrayweather.service")


@dataclass
class VerificationResult:
    source: str
    temperature: float | None
    error: str | None = None


@dataclass
class FetchResult:
    primary: WeatherSnapshot | None
    primary_error: str | None
    verifications: list[VerificationResult] = field(default_factory=list)

    def all_temps(self) -> list[float]:
        temps = []
        if self.primary:
            temps.append(self.primary.current_temperature)
        for v in self.verifications:
            if v.temperature is not None:
                temps.append(v.temperature)
        return temps


class FetchWorker(QThread):
    finished = pyqtSignal(object)

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config

    def run(self) -> None:
        cfg = self._config
        result = FetchResult(primary=None, primary_error=None)

        open_meteo = OpenMeteoClient()
        try:
            log.info("=== Fetch cycle starting for %s (%.4f, %.4f) ===",
                     cfg.location_name, cfg.latitude, cfg.longitude)
            try:
                result.primary = open_meteo.fetch_weather(
                    cfg.latitude, cfg.longitude, cfg.timezone, cfg.location_name,
                )
            except Exception as exc:
                result.primary_error = str(exc)
                log.error("Open-Meteo primary fetch failed: %s", exc)
        finally:
            open_meteo.close()

        weather_gov = WeatherGovClient()
        try:
            try:
                snap = weather_gov.fetch_temperature(cfg.latitude, cfg.longitude)
                result.verifications.append(VerificationResult(
                    source="Weather.gov", temperature=snap.current_temperature,
                ))
            except Exception as exc:
                result.verifications.append(VerificationResult(
                    source="Weather.gov", temperature=None, error=str(exc),
                ))
                log.warning("Weather.gov verification failed: %s", exc)
        finally:
            weather_gov.close()

        wttr = WttrClient()
        try:
            try:
                snap = wttr.fetch_temperature(cfg.location_name)
                result.verifications.append(VerificationResult(
                    source="WTTR.in", temperature=snap.current_temperature,
                ))
            except Exception as exc:
                result.verifications.append(VerificationResult(
                    source="WTTR.in", temperature=None, error=str(exc),
                ))
                log.warning("WTTR.in verification failed: %s", exc)
        finally:
            wttr.close()

        temps = result.all_temps()
        if temps:
            log.info("Temperatures: primary=%s, verifications=%s",
                     f"{result.primary.current_temperature:.1f}F" if result.primary else "FAILED",
                     ", ".join(f"{v.source}={v.temperature:.1f}F" if v.temperature is not None else f"{v.source}=FAILED({v.error})" for v in result.verifications))
            spread = max(temps) - min(temps)
            log.info("Temp spread: %.1fF across %d sources", spread, len(temps))
            if spread > 5.0:
                log.warning("Large temperature spread (%.1fF) — sources may be disagreeing", spread)
        else:
            log.error("All weather sources failed")

        self.finished.emit(result)


class WeatherService(QObject):
    weather_updated = pyqtSignal(object, object)

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self._config = config
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
            log.info("Refresh requested but previous fetch still running, skipping")
            return
        self._worker = FetchWorker(self._config)
        self._worker.finished.connect(self._on_fetch_finished)
        self._worker.start()

    def _on_fetch_finished(self, result: FetchResult) -> None:
        if result.primary:
            self._cache = result.primary
            error = None
        else:
            error = result.primary_error or "All weather sources failed"

        for v in result.verifications:
            if v.temperature is None:
                log.warning("Verification source %s failed: %s", v.source, v.error)

        self.weather_updated.emit(self._cache, error)

    def close(self) -> None:
        self._timer.stop()
        if self._worker and self._worker.isRunning():
            self._worker.wait(5000)
        log.info("WeatherService closed")
