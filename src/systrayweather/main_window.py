from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from systrayweather.views.daily_view import DailyView
from systrayweather.views.hourly_view import HourlyView
from systrayweather.views.weekly_view import WeeklyView
from systrayweather.weather.models import WeatherSnapshot


class MainWindow(QMainWindow):
    location_change_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("SysTrayWeather")
        self.resize(640, 480)
        self.setMinimumSize(480, 360)

        self._header = QLabel("Loading weather…")
        self._header.setStyleSheet("font-size: 16px; font-weight: 600;")

        self._location_btn = QPushButton("Location")
        self._location_btn.setToolTip("Change city or zip code")
        self._location_btn.clicked.connect(self.location_change_requested.emit)

        self._updated = QLabel("")
        self._updated.setStyleSheet("color: #888; font-size: 11px;")

        header_row = QHBoxLayout()
        header_row.addWidget(self._header, stretch=1)
        header_row.addWidget(self._location_btn)

        self._nav = QListWidget()
        self._nav.setFixedWidth(120)
        for name in ("Hourly", "Daily", "Weekly"):
            item = QListWidgetItem(name)
            self._nav.addItem(item)
        self._nav.setCurrentRow(0)

        self._hourly = HourlyView()
        self._daily = DailyView()
        self._weekly = WeeklyView()

        self._stack = QStackedWidget()
        self._stack.addWidget(self._hourly)
        self._stack.addWidget(self._daily)
        self._stack.addWidget(self._weekly)

        content = QHBoxLayout()
        content.addWidget(self._nav)
        content.addWidget(self._stack, stretch=1)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addLayout(header_row)
        layout.addWidget(self._updated)
        layout.addLayout(content)
        self.setCentralWidget(central)

        self._nav.currentRowChanged.connect(self._stack.setCurrentIndex)

        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background-color: #1e1e1e;
                color: #eee;
            }
            QPushButton {
                background-color: #3d6ea8;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                color: #fff;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #4a7fbd;
            }
            QListWidget {
                background-color: #2a2a2a;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 10px 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #3d6ea8;
            }
            """
        )

    def update_weather(self, snapshot: WeatherSnapshot | None, error: str | None = None) -> None:
        if snapshot:
            self._header.setText(
                f"{snapshot.location_name} — {round(snapshot.current_temperature)}°"
            )
            self._updated.setText(
                f"Updated {snapshot.updated_at.strftime('%I:%M %p').lstrip('0')}"
            )
        elif error:
            self._header.setText("Weather unavailable")
            self._updated.setText(f"Error: {error}")
        self._hourly.update_weather(snapshot)
        self._daily.update_weather(snapshot)
        self._weekly.update_weather(snapshot)

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()
