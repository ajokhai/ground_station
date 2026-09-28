"""
Tactical 2D Map & Coordinate Canvas for USV Swarm Operations.
Clean, high-precision CAD/map display adhering to Shadcn minimalist dark design principles.
"""

import math
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPolygonF
)
from PyQt5.QtWidgets import QWidget


class RadarWidget(QWidget):
    # Emitted when user clicks to set a new formation waypoint (x_meters, y_meters)
    waypoint_selected = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(450, 450)
        self.setMouseTracking(True)

        # View settings (pixels per meter)
        self.scale = 10.0
        self.pan_offset = QPointF(0, 0)
        self._dragging = False
        self._last_mouse_pos = None

        # Swarm data
        # Dict of usv_id -> {'x': float, 'y': float, 'heading': float, 'color': QColor, 'status': str}
        self.usvs = {}
        # Dict of usv_id -> {'x': float, 'y': float}
        self.formation_targets = {}
        self.formation_name = "V-Shape"

        # Modern Shadcn-inspired palette
        self.c_bg = QColor(12, 12, 14)           # Deep neutral zinc
        self.c_grid_subtle = QColor(28, 28, 32)   # Subtle grid line
        self.c_grid_main = QColor(39, 39, 44)     # Main axis grid
        self.c_axis = QColor(63, 63, 70)          # Center crosshair
        self.c_text_muted = QColor(113, 113, 122) # zinc-500
        self.c_text_main = QColor(244, 244, 245)  # zinc-100
        self.c_target = QColor(56, 189, 248)      # Sky blue target accent

    def set_usv_state(self, usv_id, x, y, heading=0.0, status="ONLINE"):
        if usv_id not in self.usvs:
            colors = [
                QColor(56, 189, 248),   # Sky-400
                QColor(52, 211, 153),   # Emerald-400
                QColor(251, 146, 60),   # Orange-400
                QColor(167, 139, 250),  # Violet-400
                QColor(244, 114, 182),  # Pink-400
                QColor(45, 212, 191),   # Teal-400
            ]
            idx = len(self.usvs) % len(colors)
            self.usvs[usv_id] = {
                'x': x,
                'y': y,
                'heading': heading,
                'color': colors[idx],
                'status': status,
                'trail': []
            }
        else:
            self.usvs[usv_id]['x'] = x
            self.usvs[usv_id]['y'] = y
            self.usvs[usv_id]['heading'] = heading
            self.usvs[usv_id]['status'] = status
            trail = self.usvs[usv_id].setdefault('trail', [])
            trail.append((x, y))
            if len(trail) > 30:
                trail.pop(0)

    def set_formation_targets(self, targets, name=""):
        self.formation_targets = targets
        if name:
            self.formation_name = name

    def update_animation(self):
        # Clean smooth redraw without any rotating radar sweep
        self.update()

    def reset_view(self):
        self.pan_offset = QPointF(0, 0)
        self.scale = 10.0
        self.update()

    # --- Coordinate Transformations ---
    def world_to_screen(self, wx, wy):
        cx = self.width() / 2.0 + self.pan_offset.x()
        cy = self.height() / 2.0 + self.pan_offset.y()
        # In world: +X is East (right), +Y is North (up)
        sx = cx + wx * self.scale
        sy = cy - wy * self.scale
        return QPointF(sx, sy)

    def screen_to_world(self, sx, sy):
        cx = self.width() / 2.0 + self.pan_offset.x()
        cy = self.height() / 2.0 + self.pan_offset.y()
        wx = (sx - cx) / self.scale
        wy = -(sy - cy) / self.scale
        return wx, wy

    # --- Mouse Events ---
    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and event.modifiers() & Qt.ShiftModifier):
            self._dragging = True
            self._last_mouse_pos = event.pos()
        elif event.button() == Qt.LeftButton:
            wx, wy = self.screen_to_world(event.x(), event.y())
            self.waypoint_selected.emit(wx, wy)

    def mouseMoveEvent(self, event):
        if self._dragging and self._last_mouse_pos is not None:
            delta = event.pos() - self._last_mouse_pos
            self.pan_offset += QPointF(delta.x(), delta.y())
            self._last_mouse_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() in (Qt.MiddleButton, Qt.LeftButton):
            self._dragging = False

    def wheelEvent(self, event):
        zoom_factor = 1.15 if event.angleDelta().y() > 0 else (1.0 / 1.15)
        new_scale = self.scale * zoom_factor
        if 2.0 <= new_scale <= 50.0:
            self.scale = new_scale
            self.update()

    # --- Painting ---
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx = w / 2.0 + self.pan_offset.x()
        cy = h / 2.0 + self.pan_offset.y()

        # Crisp clean background
        painter.fillRect(0, 0, w, h, self.c_bg)

        # Draw Grid & Metric Graduations
        self._draw_grid(painter, cx, cy, w, h)

        # Draw Formation Target Geometry & Lines
        self._draw_formation_targets(painter)

        # Draw USVs
        self._draw_usvs(painter)

        # Draw Minimalist HUD Overlay (Shadcn style badge)
        self._draw_hud(painter, w, h)

    def _draw_grid(self, painter, cx, cy, w, h):
        # Choose grid step based on zoom scale
        grid_step = 10.0  # meters
        if self.scale < 5.0:
            grid_step = 25.0
        elif self.scale > 20.0:
            grid_step = 5.0

        grid_px = grid_step * self.scale
        painter.setFont(QFont("Menlo", 8))

        # Vertical grid lines
        start_x = (cx % grid_px)
        curr_x = start_x
        while curr_x < w:
            is_axis = abs(curr_x - cx) < 1.0
            pen = QPen(self.c_axis if is_axis else self.c_grid_subtle, 1)
            painter.setPen(pen)
            painter.drawLine(int(curr_x), 0, int(curr_x), h)

            if not is_axis and curr_x > 20 and curr_x < w - 40:
                dist_m = (curr_x - cx) / self.scale
                painter.setPen(self.c_text_muted)
                painter.drawText(int(curr_x + 4), h - 8, f"{dist_m:+.0f}m")
            curr_x += grid_px

        # Horizontal grid lines
        start_y = (cy % grid_px)
        curr_y = start_y
        while curr_y < h:
            is_axis = abs(curr_y - cy) < 1.0
            pen = QPen(self.c_axis if is_axis else self.c_grid_subtle, 1)
            painter.setPen(pen)
            painter.drawLine(0, int(curr_y), w, int(curr_y))

            if not is_axis and curr_y > 20 and curr_y < h - 20:
                dist_m = -(curr_y - cy) / self.scale
                painter.setPen(self.c_text_muted)
                painter.drawText(8, int(curr_y - 4), f"{dist_m:+.0f}m")
            curr_y += grid_px

        # Origin Crosshair (0, 0)
        cross_pen = QPen(QColor(244, 244, 245, 180), 1.5)
        painter.setPen(cross_pen)
        painter.drawLine(int(cx - 8), int(cy), int(cx + 8), int(cy))
        painter.drawLine(int(cx), int(cy - 8), int(cx), int(cy + 8))

        painter.setPen(self.c_text_muted)
        painter.drawText(int(cx + 6), int(cy - 6), "Origin (0,0)")

    def _draw_formation_targets(self, painter):
        if not self.formation_targets:
            return

        sorted_targets = list(self.formation_targets.items())

        # Minimalist dashed formation line
        if len(sorted_targets) > 1:
            pen = QPen(QColor(56, 189, 248, 120), 1.5, Qt.DashLine)
            painter.setPen(pen)
            points = [self.world_to_screen(pos['x'], pos['y']) for _, pos in sorted_targets]
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i + 1])

        # Target slot markers: clean minimalist crosshair rings
        ring_pen = QPen(QColor(56, 189, 248, 200), 1.5, Qt.DotLine)
        painter.setFont(QFont("Menlo", 8))

        for usv_id, pos in self.formation_targets.items():
            sp = self.world_to_screen(pos['x'], pos['y'])

            # Subtle outer circle
            painter.setPen(ring_pen)
            painter.setBrush(QBrush(QColor(56, 189, 248, 20)))
            painter.drawEllipse(sp, 8, 8)

            # Center dot
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor(56, 189, 248, 240)))
            painter.drawEllipse(sp, 2, 2)

            # Label badge
            painter.setPen(QColor(244, 244, 245, 210))
            painter.drawText(int(sp.x() + 11), int(sp.y() + 4), f"Slot {usv_id}")

    def _draw_usvs(self, painter):
        painter.setFont(QFont("Helvetica Neue", 8, QFont.Bold))

        for usv_id, data in self.usvs.items():
            sp = self.world_to_screen(data['x'], data['y'])
            heading = data.get('heading', 0.0)
            color = data.get('color', QColor(56, 189, 248))

            # Breadcrumb trail
            trail = data.get('trail', [])
            if len(trail) > 1:
                trail_color = QColor(color.red(), color.green(), color.blue(), 50)
                painter.setPen(QPen(trail_color, 1.5))
                prev_pt = None
                for tx, ty in trail:
                    s_pt = self.world_to_screen(tx, ty)
                    if prev_pt is not None:
                        painter.drawLine(prev_pt, s_pt)
                    prev_pt = s_pt

            # Rotate canvas for vessel chevron
            painter.save()
            painter.translate(sp.x(), sp.y())
            angle_deg = -math.degrees(heading)
            painter.rotate(angle_deg)

            # Modern sleek chevron vessel
            vessel_poly = QPolygonF([
                QPointF(11, 0),     # Nose
                QPointF(-7, -6),    # Port
                QPointF(-4, 0),     # Notch
                QPointF(-7, 6),     # Starboard
            ])

            # Fill & border
            painter.setPen(QPen(QColor(255, 255, 255, 220), 1.5))
            painter.setBrush(QBrush(color))
            painter.drawPolygon(vessel_poly)

            # Heading vector line
            painter.setPen(QPen(QColor(255, 255, 255, 140), 1, Qt.DashLine))
            painter.drawLine(QPointF(11, 0), QPointF(22, 0))

            painter.restore()

            # Vessel Tag Pill
            tag_text = f"{usv_id}"
            fm = painter.fontMetrics()
            text_w = fm.horizontalAdvance(tag_text) + 12
            pill_rect = QRectF(sp.x() + 10, sp.y() - 18, text_w, 16)

            # Pill background
            painter.setPen(QPen(QColor(39, 39, 44), 1))
            painter.setBrush(QBrush(QColor(24, 24, 27, 220)))
            painter.drawRoundedRect(pill_rect, 4, 4)

            # Pill text
            painter.setPen(self.c_text_main)
            painter.drawText(int(sp.x() + 16), int(sp.y() - 6), tag_text)

    def _draw_hud(self, painter, w, h):
        # Minimalist Shadcn pill badge in top-left
        badge_w, badge_h = 240, 58
        badge_rect = QRectF(12, 12, badge_w, badge_h)

        # Card container
        painter.setPen(QPen(QColor(39, 39, 44), 1))
        painter.setBrush(QBrush(QColor(18, 18, 21, 230)))
        painter.drawRoundedRect(badge_rect, 6, 6)

        painter.setFont(QFont("Helvetica Neue", 8, QFont.Bold))
        painter.setPen(self.c_text_main)
        painter.drawText(22, 28, "MAP VIEWPORT")

        painter.setFont(QFont("Menlo", 8))
        painter.setPen(self.c_text_muted)
        painter.drawText(22, 44, f"Scale: {self.scale:.1f} px/m  |  Fleet: {len(self.usvs)}")
        painter.drawText(22, 58, "Left-click: Set Target  |  Wheel: Zoom")
