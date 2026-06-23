from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from systrayweather.weather.models import DayForecast
from systrayweather.widgets.weather_icon import weather_symbol


class DayRow(QWidget):
    def __init__(self, day: DayForecast, compact: bool = False, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        label_col = QVBoxLayout()
        title = QLabel(day.label)
        title.setStyleSheet("font-weight: 600;")
        date_label = QLabel(day.day.strftime("%b %d"))
        date_label.setStyleSheet("color: #888; font-size: 11px;")
        label_col.addWidget(title)
        if not compact:
            label_col.addWidget(date_label)

        temps = QLabel(f"{round(day.high)}° / {round(day.low)}°")
        temps.setAlignment(Qt.AlignmentFlag.AlignCenter)

        precip_text = ""
        if day.precipitation_probability is not None:
            precip_text = f"{round(day.precipitation_probability)}%"
        precip = QLabel(precip_text)
        precip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        precip.setStyleSheet("color: #6cb4ee; min-width: 36px;")

        symbol = QLabel(weather_symbol(day.weather_code))
        symbol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        symbol.setStyleSheet("font-size: 20px;")

        rain = QLabel("💧" if day.rainy else "")
        rain.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rain.setStyleSheet("font-size: 14px; min-width: 20px;")

        layout.addLayout(label_col, stretch=2)
        layout.addWidget(symbol)
        layout.addWidget(temps, stretch=1)
        layout.addWidget(precip)
        layout.addWidget(rain)
