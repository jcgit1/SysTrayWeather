from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication, QMessageBox

from systrayweather.config import AppConfig
from systrayweather.location_dialog import LocationDialog
from systrayweather.main_window import MainWindow
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
        self.main_window = MainWindow()
        self.tray = WeatherTrayIcon()
        self.service = WeatherService(self.config)

        self.tray.show_window_requested.connect(self._toggle_window)
        self.tray.refresh_requested.connect(self.service.refresh)
        self.tray.change_location_requested.connect(self._change_location)
        self.tray.quit_requested.connect(self._quit)
        self.main_window.location_change_requested.connect(self._change_location)
        self.service.weather_updated.connect(self._on_weather_updated)

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

    def _toggle_window(self) -> None:
        if self.main_window.isVisible():
            self.main_window.hide()
        else:
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()

    def _change_location(self) -> None:
        if _prompt_location(self.config, self.main_window):
            self.service._config = self.config
            self.service.refresh()

    def _on_weather_updated(self, snapshot, error) -> None:
        self.tray.update_weather(snapshot, error)
        self.main_window.update_weather(snapshot, error)

    def _quit(self) -> None:
        self.service.close()
        self.tray.hide()
        self.app.quit()


def main() -> None:
    sys.exit(SysTrayWeatherApp().run())


if __name__ == "__main__":
    main()
