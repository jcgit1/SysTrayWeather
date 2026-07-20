from __future__ import annotations

import signal
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication, QMessageBox

from systrayweather.config import AppConfig
from systrayweather.location_dialog import LocationDialog
from systrayweather.tray import WeatherTrayIcon
from systrayweather.weather.open_meteo import OpenMeteoClient
from systrayweather.weather_service import WeatherService

SERVER_NAME = "systrayweather_single_instance"


def _ensure_single_instance(app: QApplication) -> bool:
    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if socket.waitForConnected(500):
        socket.close()
        return False
    socket.close()

    server = QLocalServer(app)
    if not server.listen(SERVER_NAME):
        QLocalServer.removeServer(SERVER_NAME)
        server.listen(SERVER_NAME)
    return True


def _prompt_location(config: AppConfig, parent=None, required: bool = False) -> bool:
    while True:
        dialog = LocationDialog(config.location_query, parent)
        if dialog.exec() != LocationDialog.DialogCode.Accepted:
            return False
        try:
            client = OpenMeteoClient()
            try:
                result = client.geocode_location(dialog.location_query)
            finally:
                client.close()
            config.location_query = dialog.location_query
            config.location_name = result.location_name
            config.latitude = result.latitude
            config.longitude = result.longitude
            config.timezone = result.timezone
            config.location_setup_complete = True
            config.save()
            return True
        except Exception as exc:
            QMessageBox.warning(
                parent,
                "Location lookup failed",
                f"Could not find weather for \"{dialog.location_query}\":\n{exc}",
            )
            if required:
                continue
            return False


class SysTrayWeatherApp:
    def __init__(self) -> None:
        QApplication.setApplicationName("SysTrayWeather")
        QApplication.setOrganizationName("SysTrayWeather")
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        self.app = QApplication(sys.argv)
        self.config = AppConfig.load()
        self.tray = WeatherTrayIcon()
        self.service = WeatherService(self.config)

        self.tray.refresh_requested.connect(self.service.refresh)
        self.tray.change_location_requested.connect(self._change_location)
        self.tray.quit_requested.connect(self._quit)
        self.service.weather_updated.connect(self._on_weather_updated)
        self._quitting = False
        self._install_signal_handlers()

    def _install_signal_handlers(self) -> None:
        def _handle_signal(_signum, _frame) -> None:
            QTimer.singleShot(0, self._quit)

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        self._signal_timer = QTimer(self.app)
        self._signal_timer.timeout.connect(lambda: None)
        self._signal_timer.start(200)

    def run(self) -> int:
        if not _ensure_single_instance(self.app):
            QMessageBox.information(
                None,
                "SysTrayWeather",
                "SysTrayWeather is already running in the system tray.",
            )
            return 0

        if not self.config.is_configured:
            if not _prompt_location(self.config, required=True):
                return 0
            self.service._config = self.config

        self.service.start()
        self.tray.show()
        return self.app.exec()

    def _change_location(self) -> None:
        if _prompt_location(self.config):
            self.service._config = self.config
            self.service.refresh()

    def _on_weather_updated(self, snapshot, error) -> None:
        self.tray.update_weather(snapshot, error)

    def _quit(self) -> None:
        if self._quitting:
            return
        self._quitting = True
        self._signal_timer.stop()
        self.tray.shutdown()
        self.service.close()
        self.app.quit()


def main() -> None:
    sys.exit(SysTrayWeatherApp().run())


if __name__ == "__main__":
    main()
