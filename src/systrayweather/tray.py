from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from systrayweather.weather.models import WeatherSnapshot


class WeatherTrayIcon(QSystemTrayIcon):
    refresh_requested = pyqtSignal()
    change_location_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._snapshot: WeatherSnapshot | None = None

        self.setIcon(self._make_temp_icon("--"))
        self.setToolTip("SysTrayWeather")

        menu = QMenu()
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_requested.emit)
        location_action = QAction("Location…", self)
        location_action.triggered.connect(self.change_location_requested.emit)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_requested.emit)

        menu.addAction(refresh_action)
        menu.addAction(location_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.setContextMenu(menu)

    def update_weather(self, snapshot: WeatherSnapshot | None, error: str | None = None) -> None:
        self._snapshot = snapshot
        if snapshot:
            temp = round(snapshot.current_temperature)
            self.setIcon(self._make_temp_icon(f"{temp}°"))
            tip = f"{snapshot.location_name} — {temp}°"
            if error:
                tip += f"\n(update failed: {error})"
            self.setToolTip(tip)
        elif error:
            self.setToolTip(f"SysTrayWeather\n(update failed: {error})")

    def shutdown(self) -> None:
        self.hide()

    @staticmethod
    def _make_temp_icon(temp_text: str) -> QIcon:
        screen = QApplication.primaryScreen()
        ratio = screen.devicePixelRatio() if screen else 1.0
        size = int(64 * ratio)
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.GlobalColor.white)
        font = QFont("Sans Serif", int(round(28 * 1.1 * ratio)), QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, temp_text)
        painter.end()

        pixmap.setDevicePixelRatio(ratio)
        return QIcon(pixmap)
