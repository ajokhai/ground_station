"""
Tactical 2D Radar & Coordinate Display for USV Swarm Operations.
Visualizes USV real-time positions, headings, target waypoints, and formation geometry.
"""

import math
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPolygonF, QRadialGradient, QLinearGradient
)
from PyQt5.QtWidgets import QWidget


class RadarWidget(QWidget):
    # Emitted when user clicks to set a new formation waypoint (x_meters, y_meters)
    waypoint_selected = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(450, 450)
        self.setMouseTracking(True)

        # View settings (meters)
        self.scale = 8.0  # pixels per meter
        self.pan_offset = QPointF(0, 0)
        self._dragging = False
        self._last_mouse_pos = None

        # Swarm data
        # Dict of usv_id -> {'x': float, 'y': float, 'heading': float (rad), 'color': QColor, 'status': str}
        self.usvs = {}
        # Dict of usv_id -> {'x': float, 'y': float}
        self.formation_targets = {}
        self.formation_name = "V-Shape"

        # Radar sweep animation angle (degrees)
        self.sweep_angle = 0.0

    def set_usv_state(self, usv_id, x, y, heading=0.0, status="ONLINE"):
        if usv_id not in self.usvs:
            colors = [
                QColor(0, 229, 255),    # Cyan
                QColor(255, 110, 64),   # Coral / Orange
                QColor(118, 255, 3),    # Neon Green
                QColor(255, 235, 59),   # Yellow
                QColor(224, 64, 251),   # Purple
                QColor(64, 196, 255),   # Sky Blue
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
            if len(trail) > 25:
                trail.pop(0)

    def set_formation_targets(self, targets, name=""):
        self.formation_targets = targets
        if name:
            self.formation_name = name

    def update_animation(self):
        self.sweep_angle = (self.sweep_angle + 2.5) % 360.0
        self.update()

    def reset_view(self):
        self.pan_offset = QPointF(0, 0)
        self.scale = 8.0
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
        wy = (cy - sy) / self.scale
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
        if 1.5 <= new_scale <= 40.0:
            self.scale = new_scale
            self.update()

    # --- Painting ---
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx = w / 2.0 + self.pan_offset.x()
        cy = h / 2.0 + self.pan_offset.y()

        # Dark Naval Tactical Background
        bg_gradient = QRadialGradient(cx, cy, max(w, h))
        bg_gradient.setColorAt(0.0, QColor(14, 23, 34))
        bg_gradient.setColorAt(1.0, QColor(7, 12, 18))
        painter.fillRect(0, 0, w, h, bg_gradient)

        # Draw Grid & Range Rings
        self._draw_grid_and_rings(painter, cx, cy, w, h)

        # Draw Sweep Line & Glow
        self._draw_radar_sweep(painter, cx, cy, max(w, h) * 0.7)

        # Draw Formation Target Geometry & Lines
        self._draw_formation_targets(painter)

        # Draw USVs
        self._draw_usvs(painter)

        # Draw Tactical HUD Overlay
        self._draw_hud(painter, w, h)

    def _draw_grid_and_rings(self, painter, cx, cy, w, h):
        # Range Rings (e.g. every 10m, 25m, 50m, 100m depending on scale)
        ring_spacing = 10.0  # meters
        if self.scale < 4.0:
            ring_spacing = 25.0
        if self.scale < 2.0:
            ring_spacing = 50.0

        ring_pen = QPen(QColor(0, 150, 180, 45), 1, Qt.DashLine)
        axis_pen = QPen(QColor(0, 200, 255, 75), 1)
        font = QFont("Helvetica", 8)
        painter.setFont(font)

        # Center axes
        painter.setPen(axis_pen)
        painter.drawLine(0, int(cy), w, int(cy))
        painter.drawLine(int(cx), 0, int(cx), h)

        # Draw concentric rings
        max_dist = math.sqrt(max(cx, w - cx)**2 + max(cy, h - cy)**2) / self.scale
        curr_dist = ring_spacing
        painter.setPen(ring_pen)
        while curr_dist <= max_dist:
            radius_px = curr_dist * self.scale
            painter.drawEllipse(QPointF(cx, cy), radius_px, radius_px)

            # Label on east axis
            painter.setPen(QColor(0, 190, 220, 110))
            label_x = cx + radius_px + 3
            if 0 <= label_x <= w - 40:
                painter.drawText(int(label_x), int(cy - 4), f"{int(curr_dist)}m")
            painter.setPen(ring_pen)
            curr_dist += ring_spacing

        # Origin Marker
        painter.setPen(QPen(QColor(0, 255, 200, 200), 2))
        painter.setBrush(QBrush(QColor(0, 255, 200, 90)))
        painter.drawEllipse(QPointF(cx, cy), 3, 3)

    def _draw_radar_sweep(self, painter, cx, cy, max_radius):
        rad = math.radians(self.sweep_angle)
        ex = cx + math.cos(rad) * max_radius
        ey = cy - math.sin(rad) * max_radius

        sweep_pen = QPen(QColor(0, 255, 200, 70), 1.5)
        painter.setPen(sweep_pen)
        painter.drawLine(QPointF(cx, cy), QPointF(ex, ey))

    def _draw_formation_targets(self, painter):
        if not self.formation_targets:
            return

        # Connect targets with dashed formation outline
        sorted_targets = list(self.formation_targets.items())
        if len(sorted_targets) > 1:
            pen = QPen(QColor(255, 215, 64, 140), 1.5, Qt.DashDotLine)
            painter.setPen(pen)
            points = [self.world_to_screen(pos['x'], pos['y']) for _, pos in sorted_targets]
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i + 1])

        # Draw target ghost markers
        ghost_pen = QPen(QColor(255, 215, 64, 200), 1.5, Qt.DashLine)
        ghost_brush = QBrush(QColor(255, 215, 64, 40))
        font = QFont("Helvetica", 7)
        painter.setFont(font)

        for usv_id, pos in self.formation_targets.items():
            sp = self.world_to_screen(pos['x'], pos['y'])
            painter.setPen(ghost_pen)
            painter.setBrush(ghost_brush)
            painter.drawEllipse(sp, 7, 7)

            painter.setPen(QColor(255, 215, 64, 220))
            painter.drawText(int(sp.x() + 9), int(sp.y() + 4), f"T-{usv_id}")

    def _draw_usvs(self, painter):
        font = QFont("Helvetica", 8, QFont.Bold)
        painter.setFont(font)

        for usv_id, data in self.usvs.items():
            sp = self.world_to_screen(data['x'], data['y'])
            heading = data.get('heading', 0.0)
            color = data.get('color', QColor(0, 229, 255))

            # Draw trajectory trail
            trail = data.get('trail', [])
            if len(trail) > 1:
                trail_color = QColor(color.red(), color.green(), color.blue(), 60)
                trail_pen = QPen(trail_color, 1.5)
                painter.setPen(trail_pen)
                prev_pt = None
                for tx, ty in trail:
                    s_pt = self.world_to_screen(tx, ty)
                    if prev_pt is not None:
                        painter.drawLine(prev_pt, s_pt)
                    prev_pt = s_pt

            # Save state to rotate for vessel polygon
            painter.save()
            painter.translate(sp.x(), sp.y())
            # Convert ROS heading (rad, CCW from +X East) to Screen angle (deg, CW from North)
            # ROS: 0 is East (+X), pi/2 is North (+Y)
            # Qt: 0 is Right, CW.
            angle_deg = -math.degrees(heading)
            painter.rotate(angle_deg)

            # Boat silhouette polygon
            vessel_poly = QPolygonF([
                QPointF(12, 0),      # Bow (front)
                QPointF(-8, -7),     # Port stern
                QPointF(-5, 0),      # Stern notch
                QPointF(-8, 7),      # Starboard stern
            ])

            painter.setPen(QPen(color, 2))
            fill_color = QColor(color.red(), color.green(), color.blue(), 160)
            painter.setBrush(QBrush(fill_color))
            painter.drawPolygon(vessel_poly)

            # Heading vector line
            painter.setPen(QPen(QColor(255, 255, 255, 180), 1.5))
            painter.drawLine(QPointF(12, 0), QPointF(20, 0))

            painter.restore()

            # Vessel ID Label & Coordinates
            painter.setPen(QColor(255, 255, 255, 240))
            label = f"{usv_id} ({data['x']:.1f}, {data['y']:.1f})"
            painter.drawText(int(sp.x() + 14), int(sp.y() - 6), label)

    def _draw_hud(self, painter, w, h):
        # Tactical HUD elements in top-left
        hud_bg = QColor(10, 16, 24, 180)
        painter.fillRect(QRectF(10, 10, 200, 65), hud_bg)
        painter.setPen(QPen(QColor(0, 200, 255, 120), 1))
        painter.drawRect(QRectF(10, 10, 200, 65))

        painter.setPen(QColor(0, 229, 255))
        painter.setFont(QFont("Helvetica", 9, QFont.Bold))
        painter.drawText(20, 28, "TACTICAL RADAR VIEW")

        painter.setFont(QFont("Helvetica", 8))
        painter.setPen(QColor(180, 210, 230))
        painter.drawText(20, 44, f"Scale: {self.scale:.1f} px/m | Fleet: {len(self.usvs)} USVs")
        painter.drawText(20, 58, f"Formation: {self.formation_name}")
        painter.drawText(20, 70, "Left-click: Set Target | Wheel: Zoom")
