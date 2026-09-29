"""
Crisp Vector Icon Generator for USV Ground Station.
Renders razor-sharp QIcons using QPainter to ensure 100% reliable display
across all platforms and displays without font clipping or missing glyphs.
"""

from typing import Tuple
from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QPainterPath


def make_play_icon(color: QColor = QColor("#fafafa"), size: int = 32) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    # Triangle pointing right
    path = QPainterPath()
    path.moveTo(size * 0.30, size * 0.22)
    path.lineTo(size * 0.78, size * 0.50)
    path.lineTo(size * 0.30, size * 0.78)
    path.closeSubpath()

    p.fillPath(path, QBrush(color))
    p.end()
    return QIcon(pix)


def make_pause_icon(color: QColor = QColor("#fafafa"), size: int = 32) -> QIcon:
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    w = size * 0.16
    h = size * 0.56
    y = size * 0.22
    # Left bar
    p.fillRect(QRectF(size * 0.26, y, w, h), color)
    # Right bar
    p.fillRect(QRectF(size * 0.58, y, w, h), color)

    p.end()
    return QIcon(pix)


def make_rth_icon(color: QColor = QColor("#fafafa"), size: int = 32) -> QIcon:
    """Return to Home / Origin icon (circular return arrow)."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    pen = QPen(color, size * 0.11)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)

    # Arc from bottom around to top-left
    rect = QRectF(size * 0.22, size * 0.22, size * 0.56, size * 0.56)
    p.drawArc(rect, int(60 * 16), int(260 * 16))

    # Arrowhead at top-left
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(color))
    arrow = QPainterPath()
    ax, ay = size * 0.28, size * 0.34
    arrow.moveTo(ax, ay - size * 0.16)
    arrow.lineTo(ax - size * 0.16, ay + size * 0.04)
    arrow.lineTo(ax + size * 0.10, ay + size * 0.02)
    arrow.closeSubpath()
    p.fillPath(arrow, QBrush(color))

    p.end()
    return QIcon(pix)


def make_estop_icon(color: QColor = QColor("#f87171"), size: int = 32) -> QIcon:
    """E-stop octagon icon."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    # Octagon
    path = QPainterPath()
    c = size * 0.5
    r = size * 0.40
    import math
    for i in range(8):
        angle = math.radians(22.5 + i * 45)
        x = c + r * math.cos(angle)
        y = c + r * math.sin(angle)
        if i == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    path.closeSubpath()

    p.fillPath(path, QBrush(color))

    # Center minus/slash line in dark
    p.setPen(QPen(QColor("#09090b"), size * 0.13, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(size * 0.32, size * 0.5), QPointF(size * 0.68, size * 0.5))

    p.end()
    return QIcon(pix)


def make_sidebar_icon(color: QColor = QColor("#fafafa"), size: int = 32) -> QIcon:
    """macOS-style sidebar toggle icon (window with tinted left sidebar)."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    # Outer rect outline
    pen = QPen(color, size * 0.08)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    rect = QRectF(size * 0.16, size * 0.20, size * 0.68, size * 0.60)
    p.drawRoundedRect(rect, 3, 3)

    # Inner left sidebar divider
    p.drawLine(QPointF(size * 0.38, size * 0.20), QPointF(size * 0.38, size * 0.80))

    # Fill sidebar portion slightly
    sb_rect = QRectF(size * 0.16, size * 0.20, size * 0.22, size * 0.60)
    p.fillRect(sb_rect, QColor(color.red(), color.green(), color.blue(), 90))

    p.end()
    return QIcon(pix)


def make_target_icon(color: QColor = QColor("#38bdf8"), size: int = 32) -> QIcon:
    """Target / Crosshair / Center icon."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    c = size * 0.5
    pen = QPen(color, size * 0.08)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    # Outer circle
    r = size * 0.32
    p.drawEllipse(QPointF(c, c), r, r)

    # Center dot
    p.setBrush(QBrush(color))
    p.drawEllipse(QPointF(c, c), size * 0.09, size * 0.09)

    p.end()
    return QIcon(pix)


def make_close_icon(color: QColor = QColor("#a1a1aa"), size: int = 24) -> QIcon:
    """Small X icon for deselect / close."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    pen = QPen(color, size * 0.14, Qt.SolidLine, Qt.RoundCap)
    p.setPen(pen)
    pad = size * 0.28
    p.drawLine(QPointF(pad, pad), QPointF(size - pad, size - pad))
    p.drawLine(QPointF(size - pad, pad), QPointF(pad, size - pad))

    p.end()
    return QIcon(pix)


def make_rejoin_icon(color: QColor = QColor("#38bdf8"), size: int = 24) -> QIcon:
    """Swarm rejoin icon."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    pen = QPen(color, size * 0.12, Qt.SolidLine, Qt.RoundCap)
    p.setPen(pen)

    # Arc with arrow returning to center
    rect = QRectF(size * 0.18, size * 0.18, size * 0.64, size * 0.64)
    p.drawArc(rect, int(45 * 16), int(270 * 16))

    # Arrow tip
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(color))
    arrow = QPainterPath()
    ax, ay = size * 0.24, size * 0.32
    arrow.moveTo(ax, ay - size * 0.14)
    arrow.lineTo(ax - size * 0.14, ay + size * 0.06)
    arrow.lineTo(ax + size * 0.10, ay + size * 0.04)
    arrow.closeSubpath()
    p.fillPath(arrow, QBrush(color))

    p.end()
    return QIcon(pix)


def make_camera_icon(color: QColor = QColor("#38bdf8"), size: int = 32) -> QIcon:
    """Video camera icon."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)

    # Camera body (rounded rect)
    p.setBrush(QBrush(color))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(size * 0.16, size * 0.28, size * 0.44, size * 0.44), 3, 3)

    # Lens trapezoid pointing right
    lens = QPainterPath()
    lens.moveTo(size * 0.62, size * 0.38)
    lens.lineTo(size * 0.84, size * 0.26)
    lens.lineTo(size * 0.84, size * 0.74)
    lens.lineTo(size * 0.62, size * 0.62)
    lens.closeSubpath()
    p.fillPath(lens, QBrush(color))

    p.end()
    return QIcon(pix)
