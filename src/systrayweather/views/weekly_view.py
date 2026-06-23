from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from systrayweather.weather.models import WeatherSnapshot
from systrayweather.widgets.day_row import DayRow


class WeeklyView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(8)
        self._scroll.setWidget(self._container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._scroll)

        self._empty = QLabel("No weekly forecast available.")
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setStyleSheet("color: #888; padding: 24px;")

    def update_weather(self, snapshot: WeatherSnapshot | None) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not snapshot or not snapshot.weekly:
            self._layout.addWidget(self._empty)
            self._layout.addStretch()
            return

        days = snapshot.weekly[:14]
        week1 = days[:7]
        week2 = days[7:14]

        self._layout.addWidget(self._section_label("This week"))
        for day in week1:
            self._layout.addWidget(self._make_row(day))

        if week2:
            self._layout.addWidget(self._section_label("Next week"))
            for day in week2:
                self._layout.addWidget(self._make_row(day))

        self._layout.addStretch()

    def _section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet("font-weight: 700; font-size: 13px; padding: 4px 0; color: #ccc;")
        return label

    def _make_row(self, day) -> DayRow:
        row = DayRow(day, compact=True)
        row.setStyleSheet("background: rgba(255,255,255,0.04); border-radius: 6px;")
        return row
