from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from systrayweather.weather.models import WeatherSnapshot
from systrayweather.widgets.day_row import DayRow


class DailyView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(4)
        self._scroll.setWidget(self._container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._scroll)

        self._empty = QLabel("No daily forecast available.")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet("color: #888; padding: 24px;")

    def update_weather(self, snapshot: WeatherSnapshot | None) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not snapshot or not snapshot.daily:
            self._layout.addWidget(self._empty)
            self._layout.addStretch()
            return

        for day in snapshot.daily[:12]:
            row = DayRow(day)
            row.setStyleSheet(
                "background: rgba(255,255,255,0.04); border-radius: 6px;"
            )
            self._layout.addWidget(row)
        self._layout.addStretch()
