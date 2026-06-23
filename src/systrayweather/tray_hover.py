from __future__ import annotations

from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtGui import QCursor, QGuiApplication, QScreen


def cursor_in_tray_zone(cursor: QPoint | None = None, hint: QPoint | None = None) -> bool:
    """Best-effort tray hover detection when QSystemTrayIcon.geometry() is empty."""
    pos = cursor if cursor is not None else QCursor.pos()

    if hint is not None and not hint.isNull():
        hint_rect = QRect(hint.x() - 40, hint.y() - 40, 80, 80)
        if hint_rect.contains(pos):
            return True

    screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
    if screen is None:
        return False

    return _cursor_on_panel_tray_area(pos, screen)


def _cursor_on_panel_tray_area(cursor: QPoint, screen: QScreen) -> bool:
    full = screen.geometry()
    avail = screen.availableGeometry()
    w = full.width()
    h = full.height()

    # Panel thickness: use geometry delta when available, else a generous default
    # (Wayland/KDE often reports panel as overlay so avail == full).
    bottom_panel = max(full.bottom() - avail.bottom(), 0)
    top_panel = max(avail.top() - full.top(), 0)
    right_panel = max(full.right() - avail.right(), 0)
    left_panel = max(avail.left() - full.left(), 0)
    default_strip = 72

    tray_span = max(int(w * 0.35), 320)

    if bottom_panel > 0 or (bottom_panel == 0 and top_panel == 0 and right_panel == 0):
        strip = bottom_panel if bottom_panel > 0 else default_strip
        if cursor.y() >= full.bottom() - strip + 1:
            return cursor.x() >= full.right() - tray_span

    if top_panel > 0:
        strip = top_panel if top_panel > 0 else default_strip
        if cursor.y() <= full.top() + strip:
            return cursor.x() >= full.right() - tray_span

    if right_panel > 0:
        strip = right_panel if right_panel > 0 else default_strip
        if cursor.x() >= full.right() - strip + 1:
            return cursor.y() >= full.bottom() - tray_span

    if left_panel > 0:
        strip = left_panel if left_panel > 0 else default_strip
        if cursor.x() <= full.left() + strip:
            return cursor.y() >= full.bottom() - tray_span

    # Fallback: bottom-right corner (common KDE Plasma default).
    corner = QRect(full.right() - tray_span, full.bottom() - default_strip, tray_span, default_strip)
    return corner.contains(cursor)
