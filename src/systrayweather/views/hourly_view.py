from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QLabel, QScrollArea, QWidget

from systrayweather.weather.models import WeatherSnapshot
from systrayweather.widgets.weather_icon import weather_symbol


class HourlyView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setContentsMargins(12, 12, 12, 12)
        self._grid.setSpacing(8)
        self._scroll.setWidget(self._container)

        outer = QGridLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._scroll)

        self._empty = QLabel("No hourly forecast available.")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet("color: #888; padding: 24px;")

    def update_weather(self, snapshot: WeatherSnapshot | None) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not snapshot or not snapshot.hourly:
            self._grid.addWidget(self._empty, 0, 0)
            return

        headers = ["Time", "Temp", "Precip", "Conditions"]
        for col, text in enumerate(headers):
            label = QLabel(text)
            label.setStyleSheet("font-weight: 600; color: #aaa;")
            self._grid.addWidget(label, 0, col)

        for row, hour in enumerate(snapshot.hourly, start=1):
            time_label = QLabel(hour.time.strftime("%I %p").lstrip("0"))
            temp_label = QLabel(f"{round(hour.temperature)}°")
            precip = hour.precipitation_probability
            precip_label = QLabel(f"{round(precip)}%" if precip is not None else "—")
            if precip is not None and precip > 30:
                precip_label.setText(f"💧 {round(precip)}%")
            symbol = QLabel(weather_symbol(hour.weather_code))
            symbol.setStyleSheet("font-size: 18px;")

            for col, widget in enumerate((time_label, temp_label, precip_label, symbol)):
                self._grid.addWidget(widget, row, col)
