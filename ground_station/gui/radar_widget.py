"""
Tactical 2D Map Canvas for USV Swarm Operations.
Supports multiple view modes: Grid, Tactical (range rings), Minimal.
Clean, minimal Shadcn-inspired dark design.
"""

import math
import time
from typing import Optional, Dict, List
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPolygonF
from PyQt5.QtWidgets import QWidget, QMenu, QAction, QInputDialog

from ground_station.core.georeference import GeoReference, point_in_polygon, dist_to_segment
from ground_station.core.tile_manager import TileManager
from ground_station.gui.canvas_toolbar import CanvasToolbar
from ground_station.gui.datum_dialog import MARITIME_PRESETS


class RadarWidget(QWidget):
    waypoint_selected = pyqtSignal(float, float)
    individual_waypoint_selected = pyqtSignal(str, float, float)
    usv_selected = pyqtSignal(str)
    resized = pyqtSignal()
    cursor_coordinate_changed = pyqtSignal(float, float, float, float)  # (wx, wy, lat, lon)
    obstacle_added = pyqtSignal(dict)
    obstacle_removed = pyqtSignal(dict)
    obstacle_moved = pyqtSignal(dict)
    geofence_added = pyqtSignal(dict)
    geofence_removed = pyqtSignal(dict)
    measure_changed = pyqtSignal(float, float, float)  # dist_m, dist_nm, bearing_deg
    datum_changed = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        self.scale = 10.0
        self.pan_offset = QPointF(0, 0)
        self._dragging = False
        self._last_mouse_pos = None

        self.active_tool: str = 'pan'
        self._dragging_obstacle: Optional[dict] = None
        self.auto_detect_enabled: bool = True

        self.geofences: List[dict] = []
        self._drawing_geofence: List[tuple] = []
        self._measure_start: Optional[tuple] = None
        self._measure_end: Optional[tuple] = None
        self._current_mouse_world: tuple = (0.0, 0.0)
        self._hover_close_geofence: bool = False

        self.georef = GeoReference(datum_lat=37.8200, datum_lon=-122.4200)
        self.detected_obstacles: List[dict] = []

        self.tile_manager = TileManager(parent=self)
        self.tile_manager.tile_loaded.connect(lambda layer, z, x, y: self.update())

        # Floating Figma-style canvas dock
        self.toolbar = CanvasToolbar(self)
        self.toolbar.tool_changed.connect(self._on_tool_changed)
        self.toolbar.recenter_clicked.connect(self.reset_view)
        self.toolbar.clear_geofences_clicked.connect(self.clear_geofences)
        self.toolbar.show()

        self.usvs = {}
        self.formation_targets = {}
        self.custom_targets = {}
        self.formation_name = "V-Shape"
        self.selected_usv = None
        self.view_mode = "grid"  # "grid" | "tactical" | "satellite" | "nautical chart" | "minimal"

        # Palette
        self.c_bg = QColor(9, 9, 11)
        self.c_grid = QColor(20, 20, 24)
        self.c_axis = QColor(39, 39, 46)
        self.c_muted = QColor(100, 100, 110)
        self.c_text = QColor(212, 212, 216)
        self.c_accent = QColor(56, 189, 248)

    # --- Public API ---

    def set_usv_state(self, usv_id, x, y, heading=0.0, status="ONLINE"):
        if usv_id not in self.usvs:
            colors = [
                QColor(56, 189, 248),   # Sky
                QColor(52, 211, 153),   # Emerald
                QColor(251, 146, 60),   # Orange
                QColor(167, 139, 250),  # Violet
                QColor(244, 114, 182),  # Pink
                QColor(45, 212, 191),   # Teal
            ]
            self.usvs[usv_id] = {
                'x': x, 'y': y, 'heading': heading,
                'color': colors[len(self.usvs) % len(colors)],
                'status': status, 'trail': []
            }
        else:
            entry = self.usvs[usv_id]
            entry['x'], entry['y'] = x, y
            entry['heading'] = heading
            entry['status'] = status
            trail = entry.setdefault('trail', [])
            trail.append((x, y))
            if len(trail) > 40:
                trail.pop(0)

    def set_formation_targets(self, targets, name=""):
        self.formation_targets = targets
        if name:
            self.formation_name = name

    def set_view_mode(self, mode):
        """Set display mode: 'grid', 'tactical', or 'minimal'."""
        self.view_mode = mode.lower()
        self.update()

    def update_animation(self):
        self.update()

    def reset_view(self):
        self.pan_offset = QPointF(0, 0)
        self.scale = 10.0
        self.update()

    def focus_usv(self, usv_id):
        self.selected_usv = usv_id
        if usv_id in self.usvs:
            d = self.usvs[usv_id]
            self.pan_offset = QPointF(-d['x'] * self.scale, d['y'] * self.scale)
        self.update()

    # --- Coordinate Transforms ---

    def world_to_screen(self, wx, wy):
        cx = self.width() / 2.0 + self.pan_offset.x()
        cy = self.height() / 2.0 + self.pan_offset.y()
        return QPointF(cx + wx * self.scale, cy - wy * self.scale)

    def screen_to_world(self, sx, sy):
        cx = self.width() / 2.0 + self.pan_offset.x()
        cy = self.height() / 2.0 + self.pan_offset.y()
        return (sx - cx) / self.scale, -(sy - cy) / self.scale

    # --- Tool Modes & Geofence Helpers ---

    def _on_tool_changed(self, tool_name: str):
        """Handle mode switch from floating canvas dock."""
        self.active_tool = tool_name
        if tool_name != 'geofence' and self._drawing_geofence:
            self._drawing_geofence.clear()
            self._hover_close_geofence = False
        if tool_name != 'measure':
            self._measure_start = None
            self._measure_end = None

        if tool_name == 'pan':
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.CrossCursor)
        self.update()

    def add_geofence(self, points: List[tuple], name: str = "", keep_out: bool = True) -> dict:
        """Add a closed polygonal geofence / keep-out boundary."""
        if not name:
            name = f"ZONE-{len(self.geofences) + 1:02d}"
        gf = {
            'id': f"gf_{int(time.time() * 1000)}",
            'name': name,
            'points': list(points),
            'keep_out': keep_out,
            'color': QColor(239, 68, 68) if keep_out else QColor(56, 189, 248),
        }
        self.geofences.append(gf)
        self.update()
        self.geofence_added.emit(gf)
        return gf

    def remove_geofence(self, gf: dict):
        """Remove a geofence boundary."""
        if gf in self.geofences:
            self.geofences.remove(gf)
            self.update()
            self.geofence_removed.emit(gf)

    def clear_geofences(self):
        """Remove all geofence boundaries."""
        self.geofences.clear()
        self.update()

    def _commit_drawing_geofence(self):
        """Finalize the active draft geofence into a saved polygon."""
        if len(self._drawing_geofence) >= 3:
            pts = list(self._drawing_geofence)
            self._drawing_geofence.clear()
            self._hover_close_geofence = False
            self.add_geofence(pts)
        else:
            self._drawing_geofence.clear()
            self._hover_close_geofence = False
            self.update()

    def _find_geofence_at(self, sx: float, sy: float) -> Optional[dict]:
        """Check if screen coordinate (sx, sy) falls inside or near a geofence."""
        wx, wy = self.screen_to_world(sx, sy)
        for gf in reversed(self.geofences):
            pts = gf.get('points', [])
            if len(pts) >= 3:
                if point_in_polygon(wx, wy, pts):
                    return gf
                for i in range(len(pts)):
                    p1, p2 = pts[i], pts[(i + 1) % len(pts)]
                    d, _, _ = dist_to_segment(wx, wy, p1[0], p1[1], p2[0], p2[1])
                    if d * self.scale < 10.0:  # within 10 pixels of edge
                        return gf
        return None

    def _show_geofence_context_menu(self, global_pos, gf: dict):
        """Right-click menu on a keep-out geofence boundary."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #18181b;
                border: 1px solid #27272a;
                border-radius: 6px;
                color: #fafafa;
                padding: 4px;
                font-size: 11px;
            }
            QMenu::item {
                padding: 5px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #27272a;
                color: #38bdf8;
            }
            QMenu::separator {
                height: 1px;
                background: #27272a;
                margin: 4px 0;
            }
        """)
        name = gf.get('name', 'Keep-Out Zone')
        title_act = menu.addAction(f"🛑 {name}")
        title_act.setEnabled(False)
        menu.addSeparator()

        rename_act = menu.addAction("✏️ Rename Boundary...")
        delete_act = menu.addAction("🗑️ Delete This Boundary")
        clear_act = menu.addAction("⚠️ Clear All Boundaries")

        action = menu.exec_(global_pos)
        if action == rename_act:
            text, ok = QInputDialog.getText(self, "Rename Boundary", "Boundary Name:", text=name)
            if ok and text:
                gf['name'] = text.upper()
                self.update()
        elif action == delete_act:
            self.remove_geofence(gf)
        elif action == clear_act:
            self.clear_geofences()

    # --- Mouse & Keyboard Events ---

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_H:
            self.toolbar.set_active_tool('pan')
        elif key == Qt.Key_W:
            self.toolbar.set_active_tool('waypoint')
        elif key == Qt.Key_P:
            self.toolbar.set_active_tool('geofence')
        elif key == Qt.Key_B:
            self.toolbar.set_active_tool('hazard')
        elif key == Qt.Key_M:
            self.toolbar.set_active_tool('measure')
        elif key == Qt.Key_R:
            self.reset_view()
        elif key == Qt.Key_Escape:
            if self._drawing_geofence:
                self._drawing_geofence.clear()
                self._hover_close_geofence = False
                self.update()
            elif self._measure_start:
                self._measure_start = None
                self._measure_end = None
                self.update()
            elif self.selected_usv:
                self.selected_usv = None
                self.usv_selected.emit("")
                self.update()
        else:
            super().keyPressEvent(event)

    def _find_obstacle_at(self, sx: float, sy: float) -> Optional[dict]:
        """Check if screen coordinate (sx, sy) hits an obstacle circle."""
        for obs in reversed(self.detected_obstacles):
            sp = self.world_to_screen(obs['x'], obs['y'])
            r_px = max(14.0, obs.get('radius', 5.0) * self.scale)
            if math.hypot(sx - sp.x(), sy - sp.y()) <= r_px + 6:
                return obs
        return None

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton or \
           (event.button() == Qt.LeftButton and event.modifiers() & Qt.ShiftModifier):
            self._dragging = True
            self._last_mouse_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
        elif event.button() == Qt.LeftButton:
            # 1. Check if clicking on an obstacle to drag it (in pan mode)
            if self.active_tool == 'pan':
                obs_hit = self._find_obstacle_at(event.x(), event.y())
                if obs_hit:
                    self._dragging_obstacle = obs_hit
                    self.setCursor(Qt.ClosedHandCursor)
                    return

            # 2. Check if clicking on a USV (in pan or waypoint mode)
            if self.active_tool in ('pan', 'waypoint'):
                hit = None
                for uid, d in self.usvs.items():
                    sp = self.world_to_screen(d['x'], d['y'])
                    if math.hypot(event.x() - sp.x(), event.y() - sp.y()) < 20:
                        hit = uid
                        break
                if hit:
                    # Toggle: clicking the already selected USV deselects it
                    if self.selected_usv == hit:
                        self.selected_usv = None
                        self.usv_selected.emit("")
                    else:
                        self.selected_usv = hit
                        self.usv_selected.emit(hit)
                    self.update()
                    return

            # 3. Canvas action depending on active toolbar tool
            wx, wy = self.screen_to_world(event.x(), event.y())

            if self.active_tool == 'pan':
                # Safe pan: dragging moves the map, NEVER moves formation or waypoints!
                self._dragging = True
                self._last_mouse_pos = event.pos()
                self.setCursor(Qt.ClosedHandCursor)

            elif self.active_tool == 'waypoint':
                if self.selected_usv:
                    self.individual_waypoint_selected.emit(self.selected_usv, wx, wy)
                else:
                    self.waypoint_selected.emit(wx, wy)

            elif self.active_tool == 'hazard':
                obs = {
                    'x': wx,
                    'y': wy,
                    'radius': 6.0,
                    'label': f'HAZARD-{len(self.detected_obstacles)+1:02d}',
                    'level': 'hazard',
                    'source': 'Operator'
                }
                self.add_obstacle(obs)
                self.obstacle_added.emit(obs)

            elif self.active_tool == 'geofence':
                if len(self._drawing_geofence) >= 2:
                    sp_first = self.world_to_screen(self._drawing_geofence[0][0], self._drawing_geofence[0][1])
                    if math.hypot(event.x() - sp_first.x(), event.y() - sp_first.y()) < 14.0:
                        self._commit_drawing_geofence()
                        return
                self._drawing_geofence.append((wx, wy))
                self.update()

            elif self.active_tool == 'measure':
                if self._measure_start is None or self._measure_end is not None:
                    self._measure_start = (wx, wy)
                    self._measure_end = None
                else:
                    self._measure_end = (wx, wy)
                    dx = self._measure_end[0] - self._measure_start[0]
                    dy = self._measure_end[1] - self._measure_start[1]
                    dist_m = math.hypot(dx, dy)
                    bearing = (90.0 - math.degrees(math.atan2(dy, dx))) % 360.0
                    self.measure_changed.emit(dist_m, dist_m / 1852.0, bearing)
                self.update()

        elif event.button() == Qt.RightButton:
            if self._drawing_geofence:
                self._drawing_geofence.clear()
                self._hover_close_geofence = False
                self.update()
                return

            if self._measure_start:
                self._measure_start = None
                self._measure_end = None
                self.update()
                return

            obs_hit = self._find_obstacle_at(event.x(), event.y())
            if obs_hit:
                self._show_obstacle_context_menu(event.globalPos(), obs_hit)
                return

            gf_hit = self._find_geofence_at(event.x(), event.y())
            if gf_hit:
                self._show_geofence_context_menu(event.globalPos(), gf_hit)
                return

            wx, wy = self.screen_to_world(event.x(), event.y())
            self._show_water_context_menu(event.globalPos(), wx, wy)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.active_tool == 'geofence' and len(self._drawing_geofence) >= 3:
                self._commit_drawing_geofence()
            else:
                super().mouseDoubleClickEvent(event)

    def _show_obstacle_context_menu(self, global_pos, obs: dict):
        """Right-click menu on an obstacle."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #18181b;
                border: 1px solid #27272a;
                border-radius: 6px;
                color: #fafafa;
                padding: 4px;
                font-size: 11px;
            }
            QMenu::item {
                padding: 5px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #27272a;
                color: #38bdf8;
            }
            QMenu::separator {
                height: 1px;
                background: #27272a;
                margin: 4px 0;
            }
        """)

        lbl = obs.get('label', 'Obstacle')
        r = obs.get('radius', 5.0)
        source = obs.get('source', 'Manual')

        title_act = menu.addAction(f"⚠️ {lbl} ({r:.0f}m) · {source}")
        title_act.setEnabled(False)
        menu.addSeparator()

        edit_act = menu.addAction("✏️ Edit Radius & Label...")
        toggle_level_act = menu.addAction(f"Switch to {'Caution' if obs.get('level') == 'hazard' else 'Hazard'}")
        menu.addSeparator()
        delete_act = menu.addAction("🗑️ Delete This Obstacle")
        clear_act = menu.addAction("⚠️ Clear All Obstacles")

        action = menu.exec_(global_pos)
        if action == edit_act:
            val, ok = QInputDialog.getDouble(self, "Edit Obstacle Radius", f"Radius for {lbl} (meters):", r, 1.0, 100.0, 1)
            if ok:
                obs['radius'] = val
                self.update()
                self.obstacle_moved.emit(obs)
        elif action == toggle_level_act:
            obs['level'] = 'caution' if obs.get('level') == 'hazard' else 'hazard'
            self.update()
            self.obstacle_moved.emit(obs)
        elif action == delete_act:
            if obs in self.detected_obstacles:
                self.detected_obstacles.remove(obs)
                self.update()
                self.obstacle_removed.emit(obs)
        elif action == clear_act:
            self.clear_obstacles()

    def _show_water_context_menu(self, global_pos, wx: float, wy: float):
        """Right-click menu on open water."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #18181b;
                border: 1px solid #27272a;
                border-radius: 6px;
                color: #fafafa;
                padding: 4px;
                font-size: 11px;
            }
            QMenu::item {
                padding: 5px 12px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #27272a;
                color: #38bdf8;
            }
            QMenu::separator {
                height: 1px;
                background: #27272a;
                margin: 4px 0;
            }
        """)

        latlon = self.georef.to_latlon(wx, wy)
        coord_act = menu.addAction(f"📍 ({wx:+.1f}m, {wy:+.1f}m) · {latlon.lat:.4f}°N, {abs(latlon.lon):.4f}°W")
        coord_act.setEnabled(False)
        menu.addSeparator()

        add_buoy_act = menu.addAction("➕ Add Buoy Hazard (5m buffer)")
        add_shoal_act = menu.addAction("➕ Add Shallow Shoal (8m buffer)")
        add_custom_act = menu.addAction("➕ Custom Hazard...")
        menu.addSeparator()
        set_target_act = menu.addAction("🎯 Move Formation Target Here")
        draw_geofence_act = menu.addAction("🛑 Draw Keep-Out Boundary Here")
        measure_act = menu.addAction("📏 Measure From Here")
        set_datum_act = menu.addAction("⚓ Set GPS Datum Origin Here")

        menu.addSeparator()
        marine_menu = menu.addMenu("🌊 Jump to Sea Port / Operational Area")
        for p in MARITIME_PRESETS:
            icon = p.get('icon', '⚓')
            act = marine_menu.addAction(f"{icon} {p['name']} ({p['region']})")
            act.triggered.connect(lambda checked, la=p['lat'], lo=p['lon']: (self.set_datum(la, lo), self.datum_changed.emit(la, lo), self.reset_view()))

        if self.geofences:
            menu.addSeparator()
            clear_gf_act = menu.addAction(f"⚠️ Clear All Boundaries ({len(self.geofences)})")
        else:
            clear_gf_act = None

        action = menu.exec_(global_pos)
        if action == add_buoy_act:
            obs = {'x': wx, 'y': wy, 'radius': 5.0, 'label': f'BUOY-{len(self.detected_obstacles)+1:02d}', 'level': 'hazard', 'source': 'Operator'}
            self.add_obstacle(obs)
            self.obstacle_added.emit(obs)
        elif action == add_shoal_act:
            obs = {'x': wx, 'y': wy, 'radius': 8.0, 'label': f'SHOAL-{len(self.detected_obstacles)+1:02d}', 'level': 'caution', 'source': 'Operator'}
            self.add_obstacle(obs)
            self.obstacle_added.emit(obs)
        elif action == add_custom_act:
            text, ok = QInputDialog.getText(self, "New Hazard", "Obstacle Label:", text="HAZARD")
            if ok and text:
                radius, ok_r = QInputDialog.getDouble(self, "Buffer Radius", "Radius (meters):", 6.0, 1.0, 100.0, 1)
                if ok_r:
                    obs = {'x': wx, 'y': wy, 'radius': radius, 'label': text.upper(), 'level': 'hazard', 'source': 'Operator'}
                    self.add_obstacle(obs)
                    self.obstacle_added.emit(obs)
        elif action == set_target_act:
            self.waypoint_selected.emit(wx, wy)
        elif action == draw_geofence_act:
            self.toolbar.set_active_tool('geofence')
            self._drawing_geofence.append((wx, wy))
            self.update()
        elif action == measure_act:
            self.toolbar.set_active_tool('measure')
            self._measure_start = (wx, wy)
            self._measure_end = None
            self.update()
        elif action == set_datum_act:
            self.set_datum(latlon.lat, latlon.lon)
            self.datum_changed.emit(latlon.lat, latlon.lon)
        elif clear_gf_act and action == clear_gf_act:
            self.clear_geofences()

    def set_datum(self, lat: float, lon: float, alt: float = 0.0):
        self.georef.set_datum(lat, lon, alt)
        self.update()

    def set_obstacles(self, obstacles_list):
        self.detected_obstacles = obstacles_list
        self.update()

    def add_obstacle(self, obs_dict):
        self.detected_obstacles.append(obs_dict)
        self.update()

    def clear_obstacles(self):
        self.detected_obstacles = []
        self.update()

    def ingest_detected_obstacle(
        self, source_id: str, x: float, y: float,
        radius: float = 5.0, label: str = "HAZARD", level: str = "hazard"
    ) -> dict:
        """
        Auto-detect ingestion for real-life sensor feeds (LiDAR, Sonar, Vision) or simulators.
        Automatically deduplicates/clusters nearby detections within 4.0m.
        """
        now = time.time()
        for obs in self.detected_obstacles:
            if math.hypot(obs['x'] - x, obs['y'] - y) < 4.0:
                obs['x'] = 0.6 * obs['x'] + 0.4 * x
                obs['y'] = 0.6 * obs['y'] + 0.4 * y
                obs['radius'] = max(obs['radius'], radius)
                obs['last_seen'] = now
                obs['source'] = source_id
                self.update()
                return obs

        new_obs = {
            'x': x,
            'y': y,
            'radius': radius,
            'label': label,
            'level': level,
            'source': source_id,
            'auto_detected': True,
            'created_at': now,
            'last_seen': now
        }
        self.detected_obstacles.append(new_obs)
        self.update()
        self.obstacle_added.emit(new_obs)
        return new_obs

    def mouseMoveEvent(self, event):
        wx, wy = self.screen_to_world(event.x(), event.y())
        self._current_mouse_world = (wx, wy)
        latlon = self.georef.to_latlon(wx, wy)
        self.cursor_coordinate_changed.emit(wx, wy, latlon.lat, latlon.lon)

        # 1. Dragging an obstacle takes precedence
        if self._dragging_obstacle:
            self._dragging_obstacle['x'] = wx
            self._dragging_obstacle['y'] = wy
            self.update()
            self.obstacle_moved.emit(self._dragging_obstacle)
            return

        # 2. Panning canvas
        if self._dragging and self._last_mouse_pos:
            delta = event.pos() - self._last_mouse_pos
            self.pan_offset += QPointF(delta.x(), delta.y())
            self._last_mouse_pos = event.pos()
            self.update()
            return

        # 3. Geofence origin snap hover check
        need_update = False
        if self.active_tool == 'geofence' and len(self._drawing_geofence) >= 2:
            sp_first = self.world_to_screen(self._drawing_geofence[0][0], self._drawing_geofence[0][1])
            is_near = math.hypot(event.x() - sp_first.x(), event.y() - sp_first.y()) < 14.0
            if is_near != self._hover_close_geofence:
                self._hover_close_geofence = is_near
                need_update = True
        elif self._hover_close_geofence:
            self._hover_close_geofence = False
            need_update = True

        # 4. Rubber band redraws
        if self._drawing_geofence or (self._measure_start and not self._measure_end):
            need_update = True

        if need_update:
            self.update()

        # 5. Cursor styling based on hovering and active tool
        obs_hover = self._find_obstacle_at(event.x(), event.y())
        if obs_hover:
            self.setCursor(Qt.OpenHandCursor)
            return

        hovering_usv = False
        for uid, d in self.usvs.items():
            sp = self.world_to_screen(d['x'], d['y'])
            if math.hypot(event.x() - sp.x(), event.y() - sp.y()) < 20:
                hovering_usv = True
                break
        if hovering_usv:
            self.setCursor(Qt.PointingHandCursor)
            return

        if self.active_tool == 'geofence' and self._hover_close_geofence:
            self.setCursor(Qt.PointingHandCursor)
        elif self.active_tool == 'pan':
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.CrossCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._dragging_obstacle:
            self._dragging_obstacle = None
        if event.button() in (Qt.MiddleButton, Qt.LeftButton):
            self._dragging = False
        if self.active_tool == 'pan':
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.CrossCursor)

    def wheelEvent(self, event):
        f = 1.15 if event.angleDelta().y() > 0 else 1.0 / 1.15
        ns = self.scale * f
        if 0.000008 <= ns <= 50.0:
            self.scale = ns
            self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'toolbar') and self.toolbar:
            tb_hint = self.toolbar.sizeHint()
            tb_w = tb_hint.width()
            tb_h = tb_hint.height()
            self.toolbar.setGeometry(int((self.width() - tb_w) / 2), self.height() - tb_h - 24, tb_w, tb_h)
            self.toolbar.raise_()

        self.resized.emit()

    # --- Painting ---

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx = w / 2.0 + self.pan_offset.x()
        cy = h / 2.0 + self.pan_offset.y()

        p.fillRect(0, 0, w, h, self.c_bg)

        if self.view_mode in ("satellite", "nautical chart"):
            self._draw_map_tiles(p, w, h)
            self._draw_grid_overlay(p, cx, cy, w, h)
        elif self.view_mode == "tactical":
            self._draw_tactical(p, cx, cy, w, h)
        elif self.view_mode == "minimal":
            self._draw_minimal(p, cx, cy)
        else:
            self._draw_grid(p, cx, cy, w, h)

        self._draw_datum_marker(p)
        self._draw_geofences(p)
        self._draw_obstacles(p)
        self._draw_targets(p)
        self._draw_vessels(p)
        self._draw_measurement(p)
        self._draw_scale_bar(p, w, h)
        self._draw_env_badge(p, w, h)

    def _draw_map_tiles(self, p, w, h):
        """Draw Web Mercator tiles for Satellite Imagery or Nautical ENC charts."""
        layer = "satellite" if self.view_mode == "satellite" else "nautical_base"

        # Visible world coordinate bounding box
        min_wx, max_wy = self.screen_to_world(0, 0)
        max_wx, min_wy = self.screen_to_world(w, h)

        tiles = self.tile_manager.get_visible_tiles(
            min_wx, max_wx, min_wy, max_wy, self.georef, self.scale
        )

        p.save()
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        for z, tx, ty, rect in tiles:
            sp_tl = self.world_to_screen(rect.left(), rect.top() + rect.height())
            sp_br = self.world_to_screen(rect.right(), rect.top())

            screen_rect = QRectF(
                sp_tl.x(), sp_tl.y(),
                sp_br.x() - sp_tl.x(), sp_br.y() - sp_tl.y()
            )

            pix = self.tile_manager.get_tile(layer, z, tx, ty)
            if pix and not pix.isNull():
                p.setOpacity(0.96)
                p.drawPixmap(screen_rect.toRect(), pix)
                p.setOpacity(1.0)
            else:
                # Dark placeholder tile grid
                p.fillRect(screen_rect, QColor(14, 16, 22))
                p.setPen(QPen(QColor(28, 32, 45, 120), 1))
                p.drawRect(screen_rect)

            # In Nautical Chart mode, also overlay OpenSeaMap seamark navigation aids
            if self.view_mode == "nautical chart":
                sea_pix = self.tile_manager.get_tile("openseamap", z, tx, ty)
                if sea_pix and not sea_pix.isNull():
                    p.drawPixmap(screen_rect.toRect(), sea_pix)

        # Subtle dark veil over satellite imagery to preserve HUD contrast
        if self.view_mode == "satellite":
            p.fillRect(0, 0, w, h, QColor(9, 9, 11, 25))

        p.restore()

    def _compute_grid_step(self) -> float:
        """Calculate optimal world-meter step so grid lines are separated by 60-140 screen pixels."""
        target_m = 90.0 / max(1e-9, self.scale)
        exponent = math.floor(math.log10(target_m))
        fraction = target_m / (10 ** exponent)
        if fraction < 1.5:
            base = 1.0
        elif fraction < 3.5:
            base = 2.0
        elif fraction < 7.5:
            base = 5.0
        else:
            base = 10.0
        return max(1.0, base * (10 ** exponent))

    def _format_distance(self, meters: float) -> str:
        """Format distance into compact string (m, km, or M)."""
        sign = "+" if meters > 0 else ("-" if meters < 0 else "")
        abs_m = abs(meters)
        if abs_m >= 1_000_000:
            val = abs_m / 1_000_000
            return f"{sign}{val:.0f}M" if val.is_integer() else f"{sign}{val:.1f}M"
        elif abs_m >= 1000:
            val = abs_m / 1000
            return f"{sign}{val:.0f}k" if val.is_integer() else f"{sign}{val:.1f}k"
        else:
            return f"{sign}{abs_m:.0f}"

    def _draw_grid_overlay(self, p, cx, cy, w, h):
        """Draw faint tactical distance graticules over map imagery."""
        step = self._compute_grid_step()
        gpx = step * self.scale

        p.save()
        p.setFont(QFont("Menlo", 7))

        x = cx % gpx
        while x < w:
            on_axis = abs(x - cx) < 1
            p.setPen(QPen(QColor(56, 189, 248, 60 if on_axis else 25), 1, Qt.DashLine if not on_axis else Qt.SolidLine))
            p.drawLine(int(x), 0, int(x), h)
            if not on_axis and 40 < x < w - 40:
                p.setPen(QColor(161, 161, 170, 160))
                p.drawText(int(x + 3), h - 8, self._format_distance((x - cx) / self.scale))
            x += gpx

        y = cy % gpx
        while y < h:
            on_axis = abs(y - cy) < 1
            p.setPen(QPen(QColor(56, 189, 248, 60 if on_axis else 25), 1, Qt.DashLine if not on_axis else Qt.SolidLine))
            p.drawLine(0, int(y), w, int(y))
            if not on_axis and 24 < y < h - 24:
                p.setPen(QColor(161, 161, 170, 160))
                p.drawText(6, int(y - 4), self._format_distance(-(y - cy) / self.scale))
            y += gpx

        p.restore()

    def _draw_datum_marker(self, p):
        """Draw geographic reference datum marker at world (0, 0)."""
        sp = self.world_to_screen(0, 0)
        p.save()
        p.setRenderHint(QPainter.Antialiasing)

        # Concentric datum rings
        p.setPen(QPen(QColor(56, 189, 248, 80), 1, Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(sp, 11, 11)

        # Center reticle
        p.setPen(QPen(QColor(56, 189, 248, 180), 1))
        p.drawLine(int(sp.x() - 5), int(sp.y()), int(sp.x() + 5), int(sp.y()))
        p.drawLine(int(sp.x()), int(sp.y() - 5), int(sp.x()), int(sp.y() + 5))

        # Datum pill label
        p.setFont(QFont("SF Pro Text", 8, QFont.Medium))
        ns = "N" if self.georef.datum_lat >= 0 else "S"
        ew = "E" if self.georef.datum_lon >= 0 else "W"
        txt = f"⚓ DATUM ({abs(self.georef.datum_lat):.4f}°{ns}, {abs(self.georef.datum_lon):.4f}°{ew})"
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(txt) + 8
        rect = QRectF(sp.x() + 10, sp.y() + 4, tw, 14)
        p.setPen(QPen(QColor(56, 189, 248, 60), 1))
        p.setBrush(QBrush(QColor(9, 9, 11, 200)))
        p.drawRoundedRect(rect, 3, 3)
        p.setPen(QColor(148, 163, 184))
        p.drawText(int(sp.x() + 14), int(sp.y() + 15), txt)
        p.restore()

    def _draw_geofences(self, p: QPainter):
        """Draw keep-out boundary polygons and active drawing rubber band."""
        p.save()
        p.setRenderHint(QPainter.Antialiasing)

        # 1. Finished committed geofences
        for gf in self.geofences:
            pts = gf.get('points', [])
            if len(pts) < 3:
                continue
            name = gf.get('name', 'KEEP-OUT ZONE')
            color = gf.get('color', QColor(239, 68, 68))

            screen_pts = [self.world_to_screen(x, y) for x, y in pts]
            poly = QPolygonF(screen_pts)

            # Fill with translucent hazard crimson
            fill_c = QColor(color.red(), color.green(), color.blue(), 35)
            p.setBrush(QBrush(fill_c))
            border_pen = QPen(color, 1.8, Qt.DashLine)
            p.setPen(border_pen)
            p.drawPolygon(poly)

            # Draw vertices
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(color))
            for sp in screen_pts:
                p.drawEllipse(sp, 3.5, 3.5)

            # Draw label badge at first vertex
            first_sp = screen_pts[0]
            tag = f"🛑 {name}"
            p.setFont(QFont("SF Pro Text", 8, QFont.Bold))
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(tag) + 12
            rect = QRectF(first_sp.x() - tw / 2.0, first_sp.y() - 20, tw, 15)
            p.setPen(QPen(color, 1))
            p.setBrush(QBrush(QColor(18, 18, 22, 225)))
            p.drawRoundedRect(rect, 3, 3)
            p.setPen(QColor(254, 202, 202))
            p.drawText(int(first_sp.x() - tw / 2.0 + 6), int(first_sp.y() - 8), tag)

        # 2. In-flight active geofence drawing
        if self._drawing_geofence:
            draft_pts = [self.world_to_screen(x, y) for x, y in self._drawing_geofence]
            curr_sp = self.world_to_screen(self._current_mouse_world[0], self._current_mouse_world[1])

            # Connected lines between drafted vertices
            p.setPen(QPen(QColor(248, 113, 113, 240), 2, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            for i in range(len(draft_pts) - 1):
                p.drawLine(draft_pts[i], draft_pts[i + 1])

            # Rubber-band line from last drafted vertex to cursor
            if draft_pts:
                p.setPen(QPen(QColor(252, 165, 165, 180), 1.5, Qt.DotLine))
                p.drawLine(draft_pts[-1], curr_sp)

            # Draw drafted vertex dots
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(QColor(248, 113, 113)))
            for sp in draft_pts:
                p.drawEllipse(sp, 4, 4)

            # Origin vertex close-loop highlight
            if len(draft_pts) >= 2:
                orig_sp = draft_pts[0]
                if self._hover_close_geofence:
                    p.setPen(QPen(QColor(34, 197, 94, 255), 2))
                    p.setBrush(QBrush(QColor(34, 197, 94, 70)))
                    p.drawEllipse(orig_sp, 9, 9)

                    # Pill hint
                    tag = "✓ Click to Close Boundary"
                    p.setFont(QFont("SF Pro Text", 8, QFont.Bold))
                    fm = p.fontMetrics()
                    tw = fm.horizontalAdvance(tag) + 10
                    p.setPen(QPen(QColor(34, 197, 94), 1))
                    p.setBrush(QBrush(QColor(18, 18, 22, 230)))
                    p.drawRoundedRect(QRectF(orig_sp.x() + 12, orig_sp.y() - 10, tw, 18), 4, 4)
                    p.setPen(QColor(220, 252, 231))
                    p.drawText(int(orig_sp.x() + 17), int(orig_sp.y() + 3), tag)
                else:
                    p.setPen(QPen(QColor(248, 113, 113, 150), 1))
                    p.setBrush(Qt.NoBrush)
                    p.drawEllipse(orig_sp, 7, 7)

        p.restore()

    def _draw_obstacles(self, p):

        """Draw active obstacles detected by USVs on radar canvas."""
        if not self.detected_obstacles:
            return
        p.save()
        p.setRenderHint(QPainter.Antialiasing)

        for obs in self.detected_obstacles:
            ox = obs.get('x', 0.0)
            oy = obs.get('y', 0.0)
            r_meters = obs.get('radius', 5.0)
            r_px = max(10.0, r_meters * self.scale)
            sp = self.world_to_screen(ox, oy)
            level = obs.get('level', 'hazard')

            color_fill = QColor(239, 68, 68, 35) if level == 'hazard' else QColor(245, 158, 11, 35)
            color_border = QColor(239, 68, 68, 200) if level == 'hazard' else QColor(245, 158, 11, 200)

            # Warning buffer circle
            p.setPen(QPen(color_border, 1.5, Qt.DashLine))
            p.setBrush(QBrush(color_fill))
            p.drawEllipse(sp, r_px, r_px)

            # Center beacon cross
            p.setPen(QPen(color_border, 2))
            p.drawLine(int(sp.x() - 4), int(sp.y()), int(sp.x() + 4), int(sp.y()))
            p.drawLine(int(sp.x()), int(sp.y() - 4), int(sp.x()), int(sp.y() + 4))

            # Label tag
            lbl = obs.get('label', 'HAZARD')
            is_auto = obs.get('auto_detected', False)
            source = obs.get('source', '')
            icon = "📡" if is_auto else "⚠️"
            if is_auto and source:
                txt = f"{icon} {lbl} [{source}] ({r_meters:.0f}m)"
            else:
                txt = f"{icon} {lbl} ({r_meters:.0f}m)"

            p.setFont(QFont("SF Pro Text", 8, QFont.Bold))
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(txt) + 8
            rect = QRectF(sp.x() - tw / 2.0, sp.y() - r_px - 16, tw, 14)
            p.setPen(QPen(color_border, 1))
            p.setBrush(QBrush(QColor(15, 15, 18, 220)))
            p.drawRoundedRect(rect, 3, 3)
            p.setPen(color_border)
            p.drawText(int(sp.x() - tw / 2.0 + 4), int(sp.y() - r_px - 5), txt)

        p.restore()

    def _draw_scale_bar(self, p, w, h):
        """Draw dynamic nautical/metric scale bar at bottom-left corner."""
        p.save()
        p.setRenderHint(QPainter.Antialiasing)

        target_m = 120.0 / max(1e-9, self.scale)
        steps = [
            1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000,
            10_000, 20_000, 50_000, 100_000, 200_000, 500_000,
            1_000_000, 2_000_000, 5_000_000, 10_000_000
        ]
        chosen_m = steps[0]
        for s in steps:
            if s <= target_m:
                chosen_m = s
            else:
                break

        bar_px = chosen_m * self.scale
        nm = chosen_m / 1852.0

        bx = 16
        by = h - 14

        # Scale bracket
        p.setPen(QPen(QColor(161, 161, 170, 180), 1.5))
        p.drawLine(int(bx), int(by), int(bx + bar_px), int(by))
        p.drawLine(int(bx), int(by - 4), int(bx), int(by + 1))
        p.drawLine(int(bx + bar_px), int(by - 4), int(bx + bar_px), int(by + 1))

        # Scale text
        p.setFont(QFont("Menlo", 8, QFont.Bold))
        if chosen_m >= 1_000_000:
            metric_str = f"{chosen_m / 1_000_000:.0f}M m"
        elif chosen_m >= 1000:
            metric_str = f"{chosen_m / 1000:.0f} km"
        elif chosen_m >= 1:
            metric_str = f"{chosen_m:.0f} m"
        else:
            metric_str = f"{chosen_m:.1f} m"

        if nm >= 100:
            scale_text = f"{metric_str} · {nm:.0f} NM"
        elif nm >= 1:
            scale_text = f"{metric_str} · {nm:.1f} NM"
        elif nm >= 0.05:
            scale_text = f"{metric_str} · {nm:.2f} NM"
        else:
            scale_text = f"{metric_str} · {chosen_m * 3.28084:.0f} ft"

        p.setPen(QColor(212, 212, 216))
        p.drawText(int(bx), int(by - 5), scale_text)
        p.restore()

    def _draw_grid(self, p, cx, cy, w, h):
        """Standard metric grid with coordinate labels."""
        step = self._compute_grid_step()
        gpx = step * self.scale

        p.setFont(QFont("Menlo", 7))

        x = cx % gpx
        while x < w:
            on_axis = abs(x - cx) < 1
            p.setPen(QPen(self.c_axis if on_axis else self.c_grid, 1))
            p.drawLine(int(x), 0, int(x), h)
            if not on_axis and 40 < x < w - 40:
                p.setPen(self.c_muted)
                p.drawText(int(x + 3), h - 8, self._format_distance((x - cx) / self.scale))
            x += gpx

        y = cy % gpx
        while y < h:
            on_axis = abs(y - cy) < 1
            p.setPen(QPen(self.c_axis if on_axis else self.c_grid, 1))
            p.drawLine(0, int(y), w, int(y))
            if not on_axis and 24 < y < h - 24:
                p.setPen(self.c_muted)
                p.drawText(6, int(y - 4), self._format_distance(-(y - cy) / self.scale))
            y += gpx

        # Origin cross
        p.setPen(QPen(QColor(161, 161, 170, 90), 1))
        p.drawLine(int(cx - 5), int(cy), int(cx + 5), int(cy))
        p.drawLine(int(cx), int(cy - 5), int(cx), int(cy + 5))

    def _draw_tactical(self, p, cx, cy, w, h):
        """Range rings with compass bearings, military-style."""
        ring_pen = QPen(QColor(39, 39, 46, 160), 1)
        label_font = QFont("Menlo", 7)
        p.setFont(label_font)

        step = self._compute_grid_step()
        # Range rings from origin
        for multiplier in [1, 2, 5, 10]:
            r_m = step * multiplier
            r_px = r_m * self.scale
            if r_px < 20 or r_px > max(w, h) * 1.5:
                continue
            p.setPen(ring_pen)
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(cx, cy), r_px, r_px)
            # Range label
            p.setPen(self.c_muted)
            p.drawText(int(cx + r_px + 3), int(cy - 3), self._format_distance(r_m))

        # Compass axis lines through origin
        p.setPen(QPen(self.c_axis, 1))
        p.drawLine(int(cx), 0, int(cx), h)    # N-S
        p.drawLine(0, int(cy), w, int(cy))      # E-W

        # Diagonal bearing lines (45° increments)
        p.setPen(QPen(QColor(30, 30, 34), 1, Qt.DashLine))
        diag = max(w, h)
        for angle in [45, 135, 225, 315]:
            rad = math.radians(angle)
            dx, dy = math.cos(rad) * diag, -math.sin(rad) * diag
            p.drawLine(int(cx), int(cy), int(cx + dx), int(cy + dy))

        # Compass labels
        p.setPen(QColor(113, 113, 122))
        p.setFont(QFont("-apple-system", 9, QFont.DemiBold))
        if 0 <= cx <= w:
            p.drawText(int(cx + 5), 16, "N")
            p.drawText(int(cx + 5), h - 8, "S")
        if 0 <= cy <= h:
            p.drawText(w - 16, int(cy - 6), "E")
            p.drawText(6, int(cy - 6), "W")

        # Origin cross
        p.setPen(QPen(QColor(161, 161, 170, 120), 1.5))
        p.drawLine(int(cx - 6), int(cy), int(cx + 6), int(cy))
        p.drawLine(int(cx), int(cy - 6), int(cx), int(cy + 6))

    def _draw_minimal(self, p, cx, cy):
        """Ultra-clean: just origin marker, no grid."""
        p.setPen(QPen(QColor(161, 161, 170, 50), 1))
        p.drawLine(int(cx - 4), int(cy), int(cx + 4), int(cy))
        p.drawLine(int(cx), int(cy - 4), int(cx), int(cy + 4))

    def _draw_targets(self, p):
        # 1. Swarm formation slots
        if self.formation_targets:
            items = list(self.formation_targets.items())

            # Connecting lines between formation slots
            if len(items) > 1:
                p.setPen(QPen(QColor(56, 189, 248, 40), 1, Qt.DashLine))
                pts = [self.world_to_screen(v['x'], v['y']) for _, v in items]
                for i in range(len(pts) - 1):
                    p.drawLine(pts[i], pts[i + 1])

            # Target slot dots
            for uid, pos in items:
                # If USV has custom target, skip drawing its swarm slot or draw dimmed
                has_custom = uid in self.custom_targets
                sp = self.world_to_screen(pos['x'], pos['y'])
                alpha = 25 if has_custom else 60
                p.setPen(QPen(QColor(56, 189, 248, alpha), 1))
                p.setBrush(QBrush(QColor(56, 189, 248, 6 if has_custom else 10)))
                p.drawEllipse(sp, 6, 6)
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(QColor(56, 189, 248, 60 if has_custom else 140)))
                p.drawEllipse(sp, 1.5, 1.5)

        # 2. Individual custom waypoints
        for uid, cpos in self.custom_targets.items():
            csp = self.world_to_screen(cpos['x'], cpos['y'])
            # Amber ring
            p.setPen(QPen(QColor(251, 191, 36, 190), 1.5))
            p.setBrush(QBrush(QColor(251, 191, 36, 25)))
            p.drawEllipse(csp, 8, 8)
            # Center dot
            p.setBrush(QBrush(QColor(251, 191, 36, 230)))
            p.drawEllipse(csp, 2, 2)
            # Crosshair ticks
            p.setPen(QPen(QColor(251, 191, 36, 150), 1))
            p.drawLine(int(csp.x() - 12), int(csp.y()), int(csp.x() - 9), int(csp.y()))
            p.drawLine(int(csp.x() + 9), int(csp.y()), int(csp.x() + 12), int(csp.y()))
            p.drawLine(int(csp.x()), int(csp.y() - 12), int(csp.x()), int(csp.y() - 9))
            p.drawLine(int(csp.x()), int(csp.y() + 9), int(csp.x()), int(csp.y() + 12))
            # Waypoint label
            p.setFont(QFont("SF Pro Text", 8, QFont.Bold))
            p.setPen(QColor(251, 191, 36))
            p.drawText(int(csp.x() + 11), int(csp.y() + 3), f"{uid} Target")

    def _draw_vessels(self, p):
        tag_font = QFont("SF Pro Text", 8, QFont.DemiBold)
        p.setFont(tag_font)

        for uid, d in self.usvs.items():
            sp = self.world_to_screen(d['x'], d['y'])
            heading = d.get('heading', 0.0)
            color = d.get('color', self.c_accent)
            sel = uid == self.selected_usv

            # Guidance line
            if uid in self.custom_targets:
                ct = self.custom_targets[uid]
                ctsp = self.world_to_screen(ct['x'], ct['y'])
                p.setPen(QPen(QColor(251, 191, 36, 160), 1, Qt.DashLine))
                p.drawLine(sp, ctsp)
            elif sel and uid in self.formation_targets:
                t = self.formation_targets[uid]
                tsp = self.world_to_screen(t['x'], t['y'])
                p.setPen(QPen(QColor(56, 189, 248, 60), 1, Qt.DashLine))
                p.drawLine(sp, tsp)

            # Selection ring
            if sel:
                p.setPen(QPen(QColor(56, 189, 248, 110), 1.5))
                p.setBrush(QBrush(QColor(56, 189, 248, 8)))
                p.drawEllipse(sp, 18, 18)

            # Trail
            trail = d.get('trail', [])
            if len(trail) > 1:
                p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 22), 1))
                prev = None
                for tx, ty in trail:
                    pt = self.world_to_screen(tx, ty)
                    if prev:
                        p.drawLine(prev, pt)
                    prev = pt

            # Chevron
            p.save()
            p.translate(sp.x(), sp.y())
            p.rotate(-math.degrees(heading))
            poly = QPolygonF([
                QPointF(9, 0), QPointF(-5, -4.5),
                QPointF(-3, 0), QPointF(-5, 4.5),
            ])
            p.setPen(QPen(QColor(255, 255, 255, 200 if sel else 130), 1.5 if sel else 1))
            p.setBrush(QBrush(color))
            p.drawPolygon(poly)
            p.setPen(QPen(QColor(255, 255, 255, 50), 1, Qt.DashLine))
            p.drawLine(QPointF(9, 0), QPointF(16, 0))
            p.restore()

            # Label pill
            p.setFont(tag_font)
            tag = uid
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(tag) + 10
            pill = QRectF(sp.x() + 12, sp.y() - 13, tw, 15)
            p.setPen(QPen(self.c_accent if sel else QColor(30, 30, 34), 1))
            p.setBrush(QBrush(QColor(9, 9, 11, 210)))
            p.drawRoundedRect(pill, 3, 3)
            p.setPen(self.c_accent if sel else self.c_text)
            p.drawText(int(sp.x() + 17), int(sp.y() - 1), tag)

    def _draw_measurement(self, p: QPainter):
        """Draw ruler measurement line, end caps, and metric/nautical/bearing badge."""
        if not self._measure_start:
            return

        p.save()
        p.setRenderHint(QPainter.Antialiasing)

        p1_w = self._measure_start
        p2_w = self._measure_end if self._measure_end else self._current_mouse_world

        p1_s = self.world_to_screen(p1_w[0], p1_w[1])
        p2_s = self.world_to_screen(p2_w[0], p2_w[1])

        dx = p2_w[0] - p1_w[0]
        dy = p2_w[1] - p1_w[1]
        dist_m = math.hypot(dx, dy)
        dist_nm = dist_m / 1852.0
        # True heading from p1 to p2 in ENU (East=x, North=y)
        bearing = (90.0 - math.degrees(math.atan2(dy, dx))) % 360.0

        # Measure line
        line_pen = QPen(QColor(56, 189, 248, 220), 1.8, Qt.DashDotLine)
        p.setPen(line_pen)
        p.drawLine(p1_s, p2_s)

        # Crosshair ticks at endpoints
        p.setPen(QPen(QColor(56, 189, 248, 240), 2))
        for sp in (p1_s, p2_s):
            p.drawLine(int(sp.x() - 5), int(sp.y()), int(sp.x() + 5), int(sp.y()))
            p.drawLine(int(sp.x()), int(sp.y() - 5), int(sp.x()), int(sp.y() + 5))

        # Midpoint readout badge
        mid_x = (p1_s.x() + p2_s.x()) / 2.0
        mid_y = (p1_s.y() + p2_s.y()) / 2.0

        if dist_m >= 1000.0:
            dist_str = f"{dist_m / 1000.0:.2f} km"
        else:
            dist_str = f"{dist_m:.1f} m"
        badge_txt = f"📏 {dist_str} ({dist_nm:.2f} NM) · {bearing:03.0f}° T"

        p.setFont(QFont("SF Pro Text", 9, QFont.Bold))
        fm = p.fontMetrics()
        bw = fm.horizontalAdvance(badge_txt) + 16
        bh = 22
        badge_rect = QRectF(mid_x - bw / 2.0, mid_y - bh / 2.0, bw, bh)

        p.setPen(QPen(QColor(56, 189, 248, 160), 1))
        p.setBrush(QBrush(QColor(15, 17, 23, 230)))
        p.drawRoundedRect(badge_rect, 5, 5)

        p.setPen(QColor(224, 242, 254))
        p.drawText(int(mid_x - bw / 2.0 + 8), int(mid_y + 4), badge_txt)

        p.restore()

    def set_env_data(self, env_dict):

        self.env_data = env_dict
        self.update()

    def set_metocean_data(self, report_dict, drone_dict=None):
        self.env_data = report_dict
        self.drone_env_data = drone_dict
        self.update()

    def _draw_env_badge(self, p, w, h):
        if not hasattr(self, 'env_data') or not self.env_data:
            return
        ed = self.env_data
        w_spd = ed.get('wind_spd', 11.4)
        w_dir = int(ed.get('wind_dir', 35))
        c_spd = ed.get('current_spd', 0.8)
        c_dir = int(ed.get('current_dir', 50))
        sats = ed.get('sats', 19)

        if hasattr(self, 'drone_env_data') and self.drone_env_data:
            dr_spd = self.drone_env_data.get('wind_spd', w_spd)
            d_diff = dr_spd - w_spd
            if abs(d_diff) >= 2.0:
                text = f"💨 Rep: {w_spd:.1f}kn · Drone: {dr_spd:.1f}kn (Δ{d_diff:+.1f}kn ⚠️)   ·   🌊 Drift: {c_spd:.1f} kn   ·   📍 RTK Fixed ({sats} Sats)"
            else:
                text = f"💨 {w_spd:.1f} kn @ {w_dir:03d}°   ·   🌊 Drift: {c_spd:.1f} kn @ {c_dir:03d}°   ·   📍 RTK Fixed ({sats} Sats)"
        else:
            text = f"💨 {w_spd:.1f} kn @ {w_dir:03d}°   ·   🌊 Drift: {c_spd:.1f} kn @ {c_dir:03d}°   ·   📍 RTK Fixed ({sats} Sats)"

        p.setFont(QFont("SF Pro Text", 9, QFont.Medium))
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(text) + 20
        th = 24
        x = 14
        y = 12

        p.setPen(QPen(QColor(39, 39, 46, 200), 1))
        p.setBrush(QBrush(QColor(9, 9, 11, 220)))
        p.drawRoundedRect(QRectF(x, y, tw, th), 5, 5)

        p.setPen(QColor(212, 212, 216))
        p.drawText(int(x + 10), int(y + 16), text)

