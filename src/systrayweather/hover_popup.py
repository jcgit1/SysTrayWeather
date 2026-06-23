from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QVBoxLayout

from systrayweather.weather.models import DayForecast, WeatherSnapshot
from systrayweather.widgets.day_forecast_box import DayForecastBox


class HoverPopup(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(
            None,
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setObjectName("HoverPopup")
        self.setStyleSheet(
            """
            HoverPopup#HoverPopup {
                background-color: #2d2d2d;
                border: 1px solid #555;
                border-radius: 10px;
            }
            """
        )

        self._location = QLabel("")
        self._location.setStyleSheet(
            "font-weight: 600; font-size: 12px; color: #ccc; padding: 10px 12px 4px 12px;"
        )

        self._boxes = [
            DayForecastBox(),
            DayForecastBox(),
            DayForecastBox(),
        ]

        row = QHBoxLayout()
        row.setContentsMargins(12, 0, 12, 12)
        row.setSpacing(10)
        for box in self._boxes:
            row.addWidget(box)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._location)
        layout.addLayout(row)

    def update_weather(self, snapshot: WeatherSnapshot | None) -> None:
        if not snapshot:
            return

        screen = QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
        ratio = screen.devicePixelRatio() if screen else 1.0

        self._location.setText(snapshot.location_name)
        days: list[tuple[str, DayForecast | None]] = [
            ("Yesterday", snapshot.yesterday),
            ("Today", snapshot.today),
            ("Tomorrow", snapshot.tomorrow),
        ]
        for box, (title, day) in zip(self._boxes, days):
            box.set_day(title, day, ratio)

        self.adjustSize()

    def popup_at(self, anchor: QPoint) -> None:
        x = anchor.x() - self.width() // 2
        y = anchor.y() - self.height() - 16
        self.move(x, y)
        self.show()
        self.raise_()
