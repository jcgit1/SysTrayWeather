from __future__ import annotations

from enum import Enum

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap

from systrayweather.weather.models import DayForecast

THUNDERSTORM_CODES = {95, 96, 99}
RAIN_CODES = set(range(51, 68)) | set(range(80, 83))


class HoverScene(str, Enum):
    SUNNY = "sunny"
    PARTLY_CLOUDY = "partly_cloudy"
    RAIN = "rain"
    THUNDERSTORM = "thunderstorm"


def hover_scene_for_day(day: DayForecast | None) -> HoverScene:
    if day is None:
        return HoverScene.SUNNY

    precip = day.precipitation_probability or 0
    code = day.weather_code

    if precip >= 70 or code in THUNDERSTORM_CODES:
        return HoverScene.THUNDERSTORM
    if precip > 30 or code in RAIN_CODES:
        return HoverScene.RAIN
    if code in (1, 2, 3):
        return HoverScene.PARTLY_CLOUDY
    return HoverScene.SUNNY


def render_hover_background(
    scene: HoverScene,
    width: int,
    height: int,
    device_ratio: float = 1.0,
) -> QPixmap:
    w = int(width * device_ratio)
    h = int(height * device_ratio)
    pixmap = QPixmap(w, h)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    if scene == HoverScene.SUNNY:
        _paint_sunny(painter, w, h)
    elif scene == HoverScene.PARTLY_CLOUDY:
        _paint_partly_cloudy(painter, w, h)
    elif scene == HoverScene.RAIN:
        _paint_rain(painter, w, h)
    else:
        _paint_thunderstorm(painter, w, h)

    painter.end()
    pixmap.setDevicePixelRatio(device_ratio)
    return pixmap


def _sky_gradient(painter: QPainter, w: int, h: int, top: QColor, bottom: QColor) -> None:
    grad = QLinearGradient(0, 0, 0, h)
    grad.setColorAt(0, top)
    grad.setColorAt(1, bottom)
    painter.fillRect(0, 0, w, h, QBrush(grad))


def _draw_sun(painter: QPainter, cx: int, cy: int, radius: int) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 210, 60))
    painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)


def _draw_cloud(
    painter: QPainter,
    x: int,
    y: int,
    scale: float,
    color: QColor,
) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    r = int(14 * scale)
    bumps = [
        (x, y, r),
        (x + int(18 * scale), y - int(6 * scale), int(r * 0.9)),
        (x + int(36 * scale), y, int(r * 0.85)),
        (x + int(18 * scale), y + int(4 * scale), int(r * 0.75)),
    ]
    for bx, by, br in bumps:
        painter.drawEllipse(bx - br, by - br, br * 2, br * 2)
    painter.drawRoundedRect(
        x - r,
        y - int(4 * scale),
        int(52 * scale),
        int(22 * scale),
        int(10 * scale),
        int(10 * scale),
    )


def _draw_rain_drops(painter: QPainter, w: int, h: int, count: int = 12) -> None:
    pen = QPen(QColor(120, 180, 255, 200))
    pen.setWidth(max(2, w // 50))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    step = w // (count + 1)
    for i in range(count):
        x = step * (i + 1)
        y = int(h * 0.55)
        painter.drawLine(x, y, x - 4, y + int(h * 0.22))


def _draw_lightning(painter: QPainter, cx: int, cy: int, scale: float) -> None:
    path = QPainterPath()
    s = scale
    path.moveTo(cx, cy)
    path.lineTo(cx - int(8 * s), cy + int(18 * s))
    path.lineTo(cx + int(2 * s), cy + int(18 * s))
    path.lineTo(cx - int(6 * s), cy + int(38 * s))
    path.lineTo(cx + int(10 * s), cy + int(14 * s))
    path.lineTo(cx + int(2 * s), cy + int(14 * s))
    path.closeSubpath()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 230, 80))
    painter.drawPath(path)


def _paint_sunny(painter: QPainter, w: int, h: int) -> None:
    _sky_gradient(painter, w, h, QColor(90, 170, 240), QColor(140, 200, 255))
    _draw_sun(painter, int(w * 0.72), int(h * 0.28), int(min(w, h) * 0.16))


def _paint_partly_cloudy(painter: QPainter, w: int, h: int) -> None:
    _sky_gradient(painter, w, h, QColor(90, 170, 240), QColor(155, 205, 255))
    _draw_sun(painter, int(w * 0.68), int(h * 0.26), int(min(w, h) * 0.14))
    cloud = QColor(235, 240, 248, 230)
    _draw_cloud(painter, int(w * 0.12), int(h * 0.22), 1.0, cloud)
    _draw_cloud(painter, int(w * 0.38), int(h * 0.34), 0.85, QColor(210, 218, 230, 220))


def _paint_rain(painter: QPainter, w: int, h: int) -> None:
    _sky_gradient(painter, w, h, QColor(70, 90, 115), QColor(100, 120, 145))
    cloud = QColor(180, 188, 198)
    _draw_cloud(painter, int(w * 0.05), int(h * 0.12), 1.15, cloud)
    _draw_cloud(painter, int(w * 0.32), int(h * 0.08), 1.0, QColor(160, 168, 180))
    _draw_cloud(painter, int(w * 0.18), int(h * 0.28), 0.9, QColor(145, 155, 168))
    _draw_rain_drops(painter, w, h, 14)


def _paint_thunderstorm(painter: QPainter, w: int, h: int) -> None:
    _sky_gradient(painter, w, h, QColor(35, 42, 58), QColor(55, 62, 78))
    cloud = QColor(95, 102, 115)
    _draw_cloud(painter, int(w * 0.08), int(h * 0.10), 1.2, cloud)
    _draw_cloud(painter, int(w * 0.30), int(h * 0.06), 1.05, QColor(75, 82, 95))
    _draw_cloud(painter, int(w * 0.20), int(h * 0.24), 0.95, QColor(65, 72, 85))
    _draw_lightning(painter, int(w * 0.52), int(h * 0.30), min(w, h) / 55)
    _draw_rain_drops(painter, w, h, 10)
