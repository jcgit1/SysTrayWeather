from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QLabel

from systrayweather.weather.models import DayForecast
from systrayweather.widgets.hover_art import hover_scene_for_day, render_hover_background


class DayForecastBox(QFrame):
    BOX_WIDTH = 108
    BOX_HEIGHT = 118

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(self.BOX_WIDTH, self.BOX_HEIGHT)
        self.setObjectName("DayForecastBox")

        self._bg = QLabel(self)
        self._bg.setGeometry(0, 0, self.BOX_WIDTH, self.BOX_HEIGHT)
        self._bg.setScaledContents(True)

        self._title = QLabel(self)
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setStyleSheet(
            "color: #fff; font-weight: 700; font-size: 11px;"
            "background: rgba(0, 0, 0, 0.35); border-radius: 4px; padding: 2px 6px;"
        )
        self._title.setGeometry(6, 6, self.BOX_WIDTH - 12, 20)

        self._temps = QLabel(self)
        self._temps.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._temps.setFont(QFont("Sans Serif", 13, QFont.Weight.Bold))
        self._temps.setStyleSheet(
            "color: #fff;"
            "background: rgba(0, 0, 0, 0.45);"
            "border-radius: 6px;"
            "padding: 4px 6px;"
        )
        self._temps.setGeometry(8, 52, self.BOX_WIDTH - 16, 44)

        self._rain = QLabel(self)
        self._rain.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rain.setStyleSheet("font-size: 13px; background: transparent;")
        self._rain.setGeometry(0, self.BOX_HEIGHT - 22, self.BOX_WIDTH, 18)

        self._bg.lower()
        self._title.raise_()
        self._temps.raise_()
        self._rain.raise_()

        self.setStyleSheet(
            """
            DayForecastBox#DayForecastBox {
                border: 1px solid #555;
                border-radius: 8px;
                background: #1a1a1a;
            }
            """
        )

    def set_day(self, title: str, day: DayForecast | None, device_ratio: float = 1.0) -> None:
        self._title.setText(title)
        scene = hover_scene_for_day(day)
        pixmap = render_hover_background(
            scene,
            self.BOX_WIDTH,
            self.BOX_HEIGHT,
            device_ratio,
        )
        self._bg.setPixmap(pixmap)

        if day is None:
            self._temps.setText("—")
            self._rain.setText("")
            return

        self._temps.setText(f"{round(day.high)}°\n{round(day.low)}°")
        self._rain.setText("💧" if day.rainy else "")
