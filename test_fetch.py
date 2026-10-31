from __future__ import annotations

import sys
import time
from PyQt6.QtWidgets import QApplication

from systrayweather.config import AppConfig
from systrayweather.logging_setup import setup_logging
from systrayweather.weather.open_meteo import OpenMeteoClient
from systrayweather.weather.weather_gov import WeatherGovClient
from systrayweather.weather.wttr import WttrClient
import logging

log = logging.getLogger("systrayweather.test")

NUM_FETCHES = 5
INTERVAL_SEC = 20


def do_fetch(config) -> None:
    om = OpenMeteoClient()
    try:
        snap = om.fetch_weather(config.latitude, config.longitude, config.timezone, config.location_name)
        log.info("Primary (Open-Meteo): %.1fF", snap.current_temperature)
    except Exception as exc:
        log.error("Primary (Open-Meteo) failed: %s", exc)
    finally:
        om.close()

    wg = WeatherGovClient()
    try:
        snap = wg.fetch_temperature(config.latitude, config.longitude)
        log.info("Verification (Weather.gov): %.1fF", snap.current_temperature)
    except Exception as exc:
        log.error("Verification (Weather.gov) failed: %s", exc)
    finally:
        wg.close()

    wt = WttrClient()
    try:
        snap = wt.fetch_temperature(config.location_name)
        log.info("Verification (WTTR.in): %.1fF", snap.current_temperature)
    except Exception as exc:
        log.error("Verification (WTTR.in) failed: %s", exc)
    finally:
        wt.close()


def main() -> int:
    setup_logging()
    app = QApplication(sys.argv)
    config = AppConfig.load()

    log.info("Test config: %s (%.4f, %.4f)", config.location_name, config.latitude, config.longitude)
    log.info("Running %d fetches at %ds intervals", NUM_FETCHES, INTERVAL_SEC)

    for i in range(1, NUM_FETCHES + 1):
        log.info("=== Fetch %d/%d ===", i, NUM_FETCHES)
        do_fetch(config)

        if i < NUM_FETCHES:
            log.info("Waiting %ds before next fetch...", INTERVAL_SEC)
            end = time.time() + INTERVAL_SEC
            while time.time() < end:
                app.processEvents()
                time.sleep(0.2)

    log.info("=== Test complete ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
