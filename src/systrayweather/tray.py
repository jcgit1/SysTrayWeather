from __future__ import annotations

import time

from PyQt6.QtCore import QEvent, QPoint, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QCursor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from systrayweather.hover_popup import HoverPopup
from systrayweather.tray_hover import cursor_in_tray_zone
from systrayweather.weather.models import WeatherSnapshot


class WeatherTrayIcon(QSystemTrayIcon):
    show_window_requested = pyqtSignal()
    refresh_requested = pyqtSignal()
    change_location_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._popup = HoverPopup()
        self._snapshot: WeatherSnapshot | None = None
        self._popup_visible = False
        self._hover_dwell_ms = 0
        self._tray_hint = QPoint()
        self._tray_hint_at = 0.0

        self.setIcon(self._make_temp_icon("--"))
        # Disable native SNI tooltip; KDE would show plain text instead of our popup.
        self.setToolTip("")

        menu = QMenu()
        forecast_action = QAction("Show forecast", self)
        forecast_action.triggered.connect(self._show_forecast_at_cursor)
        show_action = QAction("Show window", self)
        show_action.triggered.connect(self.show_window_requested.emit)
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.refresh_requested.emit)
        location_action = QAction("Location…", self)
        location_action.triggered.connect(self.change_location_requested.emit)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_requested.emit)

        menu.addAction(forecast_action)
        menu.addAction(show_action)
        menu.addAction(refresh_action)
        menu.addAction(location_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        menu.aboutToShow.connect(self._remember_tray_cursor)
        self.setContextMenu(menu)

        self.activated.connect(self._on_activated)

        self._hover_timer = QTimer(self)
        self._hover_timer.setInterval(80)
        self._hover_timer.timeout.connect(self._check_hover)
        self._hover_timer.start()

    def update_weather(self, snapshot: WeatherSnapshot | None, error: str | None = None) -> None:
        self._snapshot = snapshot
        if snapshot:
            self.setIcon(self._make_temp_icon(f"{round(snapshot.current_temperature)}°"))
            self.setToolTip("")
            self._popup.update_weather(snapshot)
        elif error:
            self.setToolTip("")

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.ToolTip and self._snapshot:
            self._show_hover_popup(QCursor.pos())
            return True
        return super().event(event)

    def _remember_tray_cursor(self) -> None:
        self._tray_hint = QCursor.pos()
        self._tray_hint_at = time.monotonic()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        self._remember_tray_cursor()
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._hide_hover_popup()
            self.show_window_requested.emit()

    def _check_hover(self) -> None:
        if not self._snapshot:
            self._hover_dwell_ms = 0
            return

        cursor = QCursor.pos()
        hint = self._tray_hint if time.monotonic() - self._tray_hint_at < 120 else None
        over_tray = self._cursor_over_tray_icon(cursor, hint)
        over_popup = self._popup_visible and self._popup.frameGeometry().contains(cursor)

        if over_tray:
            self._hover_dwell_ms += self._hover_timer.interval()
            if not self._popup_visible and self._hover_dwell_ms >= 250:
                self._show_hover_popup(cursor)
        elif over_popup:
            self._hover_dwell_ms = 250
        else:
            self._hover_dwell_ms = 0
            if self._popup_visible:
                self._hide_hover_popup()

    def _cursor_over_tray_icon(self, cursor: QPoint, hint: QPoint | None) -> bool:
        geom = self.geometry()
        if not geom.isNull():
            return geom.adjusted(-8, -8, 8, 8).contains(cursor)
        return cursor_in_tray_zone(cursor, hint)

    def _show_forecast_at_cursor(self) -> None:
        self._remember_tray_cursor()
        self._show_hover_popup(QCursor.pos())

    def _show_hover_popup(self, anchor: QPoint | None = None) -> None:
        if not self._snapshot:
            return

        self._popup.update_weather(self._snapshot)
        self._popup.adjustSize()

        pos = anchor or QCursor.pos()
        geom = self.geometry()
        if not geom.isNull():
            pos = geom.center()
            pos = QPoint(pos.x(), geom.top())

        self._popup.popup_at(pos)
        self._popup_visible = True

    def _hide_hover_popup(self) -> None:
        self._popup.hide()
        self._popup_visible = False
        self._hover_dwell_ms = 0

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
