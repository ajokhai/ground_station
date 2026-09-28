"""
HERMORD Ground Station Main Window.
Provides USV Swarm status monitoring, tactical radar visualization,
formation control, and ROS 2 communication.
"""

import sys
import math
import time
import json
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QIcon
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QSlider, QTableWidget,
    QTableWidgetItem, QHeaderView, QTextEdit, QGroupBox,
    QCheckBox, QFrame, QSplitter, QProgressBar
)

from ground_station.gui.radar_widget import RadarWidget


DARK_STYLESHEET = """
QMainWindow {
    background-color: #0b1118;
    color: #e2e8f0;
}
QWidget {
    font-family: "Helvetica Neue", "Arial";
    color: #e2e8f0;
}
QGroupBox {
    border: 1px solid #1e293b;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 10px;
    background-color: #111a26;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: #38bdf8;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    left: 12px;
}
QTableWidget {
    background-color: #0d1520;
    border: 1px solid #1e293b;
    border-radius: 6px;
    gridline-color: #1e293b;
    color: #e2e8f0;
    selection-background-color: #0284c7;
    selection-color: #ffffff;
}
QHeaderView::section {
    background-color: #162232;
    color: #94a3b8;
    padding: 6px;
    border: 1px solid #1e293b;
    font-weight: bold;
    font-size: 11px;
}
QPushButton {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #334155;
    border-color: #475569;
}
QPushButton:pressed {
    background-color: #0f172a;
}
QPushButton#deployBtn {
    background-color: #0284c7;
    border-color: #38bdf8;
    color: #ffffff;
}
QPushButton#deployBtn:hover {
    background-color: #0369a1;
}
QPushButton#rthBtn {
    background-color: #059669;
    border-color: #34d399;
    color: #ffffff;
}
QPushButton#rthBtn:hover {
    background-color: #047857;
}
QPushButton#estopBtn {
    background-color: #dc2626;
    border-color: #f87171;
    color: #ffffff;
    font-size: 13px;
    font-weight: bold;
}
QPushButton#estopBtn:hover {
    background-color: #b91c1c;
}
QComboBox {
    background-color: #162232;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f8fafc;
}
QComboBox::drop-down {
    border: none;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #1e293b;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #0284c7;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #38bdf8;
    border: 2px solid #0c4a6e;
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}
QTextEdit {
    background-color: #080d14;
    border: 1px solid #1e293b;
    border-radius: 6px;
    color: #38bdf8;
    font-family: Menlo, Monaco, monospace;
    font-size: 11px;
}
QProgressBar {
    border: 1px solid #334155;
    border-radius: 4px;
    text-align: center;
    background-color: #1e293b;
    color: white;
    font-size: 10px;
    font-weight: bold;
}
QProgressBar::chunk {
    background-color: #10b981;
    border-radius: 3px;
}
"""


class MainWindow(QMainWindow):
    # Signals to communicate with ROS 2 node
    formation_command_signal = pyqtSignal(dict)
    emergency_stop_signal = pyqtSignal(bool)

    def __init__(self, ros_node=None):
        super().__init__()
        self.ros_node = ros_node
        self.setWindowTitle("HERMORD - USV Swarm Ground Station")
        self.resize(1200, 780)
        self.setStyleSheet(DARK_STYLESHEET)

        # Swarm State
        self.formation_center = {'x': 0.0, 'y': 0.0}
        self.formation_type = "V-Shape"
        self.formation_spacing = 15.0  # meters
        self.formation_heading = 90.0  # degrees (East)
        self.simulation_enabled = True

        # Initialize USVs (4 standard USVs)
        self.usv_fleet = {
            'USV-1': {'x': -15.0, 'y': -15.0, 'heading': 0.0, 'speed': 0.0, 'battery': 94.0, 'status': 'IDLE'},
            'USV-2': {'x': -10.0, 'y': -25.0, 'heading': 0.0, 'speed': 0.0, 'battery': 88.0, 'status': 'IDLE'},
            'USV-3': {'x': 10.0,  'y': -25.0, 'heading': 0.0, 'speed': 0.0, 'battery': 91.0, 'status': 'IDLE'},
            'USV-4': {'x': 15.0,  'y': -15.0, 'heading': 0.0, 'speed': 0.0, 'battery': 85.0, 'status': 'IDLE'},
        }

        self.start_time = time.time()
        self._init_ui()
        self._calculate_formation_targets()

        # Animation & Physics Timer (30 Hz)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._tick)
        self.anim_timer.start(33)

        self.log_event("Ground Station GUI Initialized. Ready for Swarm Coordination.")

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 10, 12, 12)
        main_layout.setSpacing(10)

        # 1. Top Bar
        main_layout.addWidget(self._create_top_bar())

        # 2. Main Content (Splitter: Left Panel, Center Radar, Right Controls)
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._create_fleet_panel())
        splitter.addWidget(self._create_radar_panel())
        splitter.addWidget(self._create_control_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 5)
        splitter.setStretchFactor(2, 3)
        main_layout.addWidget(splitter, stretch=1)

        # 3. Bottom Log Console
        main_layout.addWidget(self._create_log_panel())

    def _create_top_bar(self):
        bar = QFrame()
        bar.setStyleSheet("background-color: #111a26; border-radius: 8px; border: 1px solid #1e293b; padding: 4px;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 6, 12, 6)

        # Title
        title_label = QLabel("HERMORD GROUND STATION // USV SWARM")
        title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #38bdf8; letter-spacing: 1px;")
        layout.addWidget(title_label)

        layout.addStretch()

        # ROS 2 Status Badge
        self.ros_badge = QLabel("● ROS 2: ONLINE")
        self.ros_badge.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px; padding: 4px 8px; background: #064e3b; border-radius: 4px;")
        layout.addWidget(self.ros_badge)

        # Fleet Count Badge
        self.fleet_badge = QLabel("FLEET: 4 USVs")
        self.fleet_badge.setStyleSheet("color: #e2e8f0; font-weight: bold; font-size: 11px; padding: 4px 8px; background: #1e293b; border-radius: 4px;")
        layout.addWidget(self.fleet_badge)

        # Uptime Label
        self.uptime_label = QLabel("UPTIME: 00:00")
        self.uptime_label.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 500;")
        layout.addWidget(self.uptime_label)

        return bar

    def _create_fleet_panel(self):
        group = QGroupBox("Swarm Fleet Status")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Table of USVs
        self.fleet_table = QTableWidget(len(self.usv_fleet), 5)
        self.fleet_table.setHorizontalHeaderLabels(["ID", "Pos (m)", "Spd", "Bat", "Status"])
        self.fleet_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.fleet_table.verticalHeader().setVisible(False)
        self.fleet_table.setSelectionBehavior(QTableWidget.SelectRows)

        for row, (usv_id, data) in enumerate(self.usv_fleet.items()):
            self.fleet_table.setItem(row, 0, QTableWidgetItem(usv_id))
            self.fleet_table.setItem(row, 1, QTableWidgetItem(f"{data['x']:.1f}, {data['y']:.1f}"))
            self.fleet_table.setItem(row, 2, QTableWidgetItem(f"{data['speed']:.1f} m/s"))
            self.fleet_table.setItem(row, 3, QTableWidgetItem(f"{int(data['battery'])}%"))
            self.fleet_table.setItem(row, 4, QTableWidgetItem(data['status']))

        layout.addWidget(self.fleet_table)

        # Swarm quick stats
        stats_frame = QFrame()
        stats_frame.setStyleSheet("background-color: #0c141f; border-radius: 6px; padding: 6px;")
        s_layout = QGridLayout(stats_frame)
        s_layout.addWidget(QLabel("Avg Battery:"), 0, 0)
        self.avg_bat_lbl = QLabel("89%")
        self.avg_bat_lbl.setStyleSheet("color: #10b981; font-weight: bold;")
        s_layout.addWidget(self.avg_bat_lbl, 0, 1)

        s_layout.addWidget(QLabel("Swarm Center:"), 1, 0)
        self.swarm_center_lbl = QLabel("(0.0m, 0.0m)")
        s_layout.addWidget(self.swarm_center_lbl, 1, 1)

        layout.addWidget(stats_frame)

        # Swarm Fleet Size selector
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Fleet Count:"))
        self.fleet_count_combo = QComboBox()
        self.fleet_count_combo.addItems(["2 USVs", "3 USVs", "4 USVs", "5 USVs", "6 USVs"])
        self.fleet_count_combo.setCurrentText("4 USVs")
        self.fleet_count_combo.currentTextChanged.connect(self._on_fleet_count_changed)
        size_layout.addWidget(self.fleet_count_combo)
        layout.addLayout(size_layout)

        return group

    def _create_radar_panel(self):
        group = QGroupBox("Tactical Radar & Waypoints")
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        # Radar Widget
        self.radar = RadarWidget()
        self.radar.waypoint_selected.connect(self._on_waypoint_selected)
        layout.addWidget(self.radar, stretch=1)

        # Radar controls bar
        ctrl_bar = QHBoxLayout()
        reset_btn = QPushButton("Reset Center")
        reset_btn.clicked.connect(self.radar.reset_view)
        ctrl_bar.addWidget(reset_btn)

        zoom_in_btn = QPushButton("Zoom In (+)")
        zoom_in_btn.clicked.connect(lambda: setattr(self.radar, 'scale', min(40.0, self.radar.scale * 1.25)))
        ctrl_bar.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("Zoom Out (-)")
        zoom_out_btn.clicked.connect(lambda: setattr(self.radar, 'scale', max(1.5, self.radar.scale * 0.8)))
        ctrl_bar.addWidget(zoom_out_btn)

        self.waypoint_lbl = QLabel("Target: (0.0, 0.0)m")
        self.waypoint_lbl.setStyleSheet("color: #f59e0b; font-weight: 500; font-size: 11px;")
        ctrl_bar.addStretch()
        ctrl_bar.addWidget(self.waypoint_lbl)

        layout.addLayout(ctrl_bar)
        return group

    def _create_control_panel(self):
        group = QGroupBox("Formation & Mission Control")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # Formation Shape
        layout.addWidget(QLabel("Formation Geometry:"))
        self.form_combo = QComboBox()
        self.form_combo.addItems(["V-Shape", "Line (Abeam)", "Column (In-line)", "Circle", "Diamond"])
        self.form_combo.currentTextChanged.connect(self._on_formation_type_changed)
        layout.addWidget(self.form_combo)

        # Spacing Slider
        self.spacing_lbl = QLabel(f"Vehicle Spacing: {int(self.formation_spacing)} m")
        layout.addWidget(self.spacing_lbl)
        self.spacing_slider = QSlider(Qt.Horizontal)
        self.spacing_slider.setRange(5, 50)
        self.spacing_slider.setValue(int(self.formation_spacing))
        self.spacing_slider.valueChanged.connect(self._on_spacing_changed)
        layout.addWidget(self.spacing_slider)

        # Heading / Bearing Slider
        self.heading_lbl = QLabel(f"Formation Bearing: {int(self.formation_heading)}° (East)")
        layout.addWidget(self.heading_lbl)
        self.heading_slider = QSlider(Qt.Horizontal)
        self.heading_slider.setRange(0, 359)
        self.heading_slider.setValue(int(self.formation_heading))
        self.heading_slider.valueChanged.connect(self._on_heading_changed)
        layout.addWidget(self.heading_slider)

        # Simulation Mode Checkbox
        self.sim_checkbox = QCheckBox("Simulate Swarm Physics")
        self.sim_checkbox.setChecked(True)
        self.sim_checkbox.toggled.connect(lambda val: setattr(self, 'simulation_enabled', val))
        self.sim_checkbox.setStyleSheet("color: #38bdf8; font-weight: 500;")
        layout.addWidget(self.sim_checkbox)

        layout.addSpacing(6)

        # Action Buttons
        self.deploy_btn = QPushButton("DEPLOY FORMATION")
        self.deploy_btn.setObjectName("deployBtn")
        self.deploy_btn.setFixedHeight(36)
        self.deploy_btn.clicked.connect(self._deploy_formation)
        layout.addWidget(self.deploy_btn)

        self.hold_btn = QPushButton("HOLD / DISPERSE")
        self.hold_btn.setFixedHeight(34)
        self.hold_btn.clicked.connect(self._hold_position)
        layout.addWidget(self.hold_btn)

        self.rth_btn = QPushButton("RETURN TO HOME (RTH)")
        self.rth_btn.setObjectName("rthBtn")
        self.rth_btn.setFixedHeight(34)
        self.rth_btn.clicked.connect(self._return_home)
        layout.addWidget(self.rth_btn)

        layout.addSpacing(10)

        # Emergency Stop
        self.estop_btn = QPushButton("⚠ EMERGENCY STOP")
        self.estop_btn.setObjectName("estopBtn")
        self.estop_btn.setFixedHeight(44)
        self.estop_btn.clicked.connect(self._emergency_stop)
        layout.addWidget(self.estop_btn)

        layout.addStretch()
        return group

    def _create_log_panel(self):
        group = QGroupBox("ROS 2 Mission Log & Telemetry Console")
        layout = QVBoxLayout(group)
        layout.setSpacing(4)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumHeight(120)
        layout.addWidget(self.log_console)

        return group

    # --- Formation Geometry Calculations ---
    def _calculate_formation_targets(self):
        targets = {}
        usv_ids = list(self.usv_fleet.keys())
        n = len(usv_ids)
        if n == 0:
            return targets

        cx, cy = self.formation_center['x'], self.formation_center['y']
        bearing_rad = math.radians(self.formation_heading)
        # Formation forward vector
        fx = math.cos(bearing_rad)
        fy = math.sin(bearing_rad)
        # Formation right/lateral vector (90 deg CW from forward)
        rx = math.sin(bearing_rad)
        ry = -math.cos(bearing_rad)

        d = self.formation_spacing

        if self.formation_type == "V-Shape":
            # Leader at apex, followers alternating left/right behind
            for i, usv_id in enumerate(usv_ids):
                if i == 0:
                    targets[usv_id] = {'x': cx, 'y': cy}
                else:
                    tier = (i + 1) // 2
                    side = -1 if (i % 2 == 1) else 1  # -1 is port/left, +1 is starboard/right
                    tx = cx - tier * d * fx + side * tier * d * rx
                    ty = cy - tier * d * fy + side * tier * d * ry
                    targets[usv_id] = {'x': tx, 'y': ty}

        elif self.formation_type == "Line (Abeam)":
            # Lateral line perpendicular to heading
            mid = (n - 1) / 2.0
            for i, usv_id in enumerate(usv_ids):
                offset = (i - mid) * d
                tx = cx + offset * rx
                ty = cy + offset * ry
                targets[usv_id] = {'x': tx, 'y': ty}

        elif self.formation_type == "Column (In-line)":
            # Single file line along heading vector
            mid = (n - 1) / 2.0
            for i, usv_id in enumerate(usv_ids):
                offset = (mid - i) * d
                tx = cx + offset * fx
                ty = cy + offset * fy
                targets[usv_id] = {'x': tx, 'y': ty}

        elif self.formation_type == "Circle":
            radius = max(d, (n * d) / (2 * math.pi))
            for i, usv_id in enumerate(usv_ids):
                angle = bearing_rad + (2 * math.pi * i / n)
                tx = cx + radius * math.cos(angle)
                ty = cy + radius * math.sin(angle)
                targets[usv_id] = {'x': tx, 'y': ty}

        elif self.formation_type == "Diamond":
            positions = [
                (1, 0),   # Front
                (0, -1),  # Left
                (0, 1),   # Right
                (-1, 0),  # Rear
            ]
            for i, usv_id in enumerate(usv_ids):
                px, py = positions[i % len(positions)]
                tier = (i // len(positions)) + 1
                tx = cx + px * tier * d * fx + py * tier * d * rx
                ty = cy + px * tier * d * fy + py * tier * d * ry
                targets[usv_id] = {'x': tx, 'y': ty}

        self.radar.set_formation_targets(targets, name=self.formation_type)
        return targets

    # --- UI Event Handlers ---
    def _on_formation_type_changed(self, text):
        self.formation_type = text
        self._calculate_formation_targets()
        self.log_event(f"Formation changed to: {text}")

    def _on_spacing_changed(self, value):
        self.formation_spacing = float(value)
        self.spacing_lbl.setText(f"Vehicle Spacing: {value} m")
        self._calculate_formation_targets()

    def _on_heading_changed(self, value):
        self.formation_heading = float(value)
        directions = ["East", "NE", "North", "NW", "West", "SW", "South", "SE", "East"]
        dir_idx = int((value + 22.5) // 45) % 8
        self.heading_lbl.setText(f"Formation Bearing: {value}° ({directions[dir_idx]})")
        self._calculate_formation_targets()

    def _on_fleet_count_changed(self, text):
        count = int(text.split()[0])
        # Rebuild fleet dict
        new_fleet = {}
        for i in range(1, count + 1):
            uid = f"USV-{i}"
            if uid in self.usv_fleet:
                new_fleet[uid] = self.usv_fleet[uid]
            else:
                new_fleet[uid] = {
                    'x': -10.0 * i, 'y': -20.0,
                    'heading': 0.0, 'speed': 0.0,
                    'battery': 95.0, 'status': 'IDLE'
                }
        self.usv_fleet = new_fleet
        self.radar.usvs.clear()
        self.fleet_badge.setText(f"FLEET: {count} USVs")
        self._update_fleet_table_structure()
        self._calculate_formation_targets()
        self.log_event(f"Swarm size updated to {count} vehicles.")

    def _update_fleet_table_structure(self):
        self.fleet_table.setRowCount(len(self.usv_fleet))
        for row, (usv_id, data) in enumerate(self.usv_fleet.items()):
            self.fleet_table.setItem(row, 0, QTableWidgetItem(usv_id))
            self.fleet_table.setItem(row, 1, QTableWidgetItem(f"{data['x']:.1f}, {data['y']:.1f}"))
            self.fleet_table.setItem(row, 2, QTableWidgetItem(f"{data['speed']:.1f} m/s"))
            self.fleet_table.setItem(row, 3, QTableWidgetItem(f"{int(data['battery'])}%"))
            self.fleet_table.setItem(row, 4, QTableWidgetItem(data['status']))

    def _on_waypoint_selected(self, wx, wy):
        self.formation_center = {'x': wx, 'y': wy}
        self.waypoint_lbl.setText(f"Target: ({wx:.1f}, {wy:.1f})m")
        self._calculate_formation_targets()
        self.log_event(f"New formation center designated at ({wx:.1f}m, {wy:.1f}m)")

    def _deploy_formation(self):
        targets = self._calculate_formation_targets()
        for usv_id in self.usv_fleet:
            self.usv_fleet[usv_id]['status'] = 'FORMATION'

        cmd = {
            'action': 'DEPLOY_FORMATION',
            'formation': self.formation_type,
            'spacing': self.formation_spacing,
            'heading_deg': self.formation_heading,
            'center': self.formation_center,
            'targets': targets,
            'timestamp': time.time()
        }
        self.formation_command_signal.emit(cmd)
        self.log_event(f"[PUB -> /ground_station/formation_cmd] Deployed {self.formation_type} to {len(targets)} USVs")

    def _hold_position(self):
        for usv_id in self.usv_fleet:
            self.usv_fleet[usv_id]['status'] = 'HOLD'
            self.usv_fleet[usv_id]['speed'] = 0.0

        cmd = {
            'action': 'HOLD',
            'timestamp': time.time()
        }
        self.formation_command_signal.emit(cmd)
        self.log_event("[PUB -> /ground_station/formation_cmd] Commanded HOLD position.")

    def _return_home(self):
        self.formation_center = {'x': 0.0, 'y': 0.0}
        self.waypoint_lbl.setText("Target: (0.0, 0.0)m [HOME]")
        self._calculate_formation_targets()
        for usv_id in self.usv_fleet:
            self.usv_fleet[usv_id]['status'] = 'RTH'

        cmd = {
            'action': 'RETURN_HOME',
            'target': {'x': 0.0, 'y': 0.0},
            'timestamp': time.time()
        }
        self.formation_command_signal.emit(cmd)
        self.log_event("[PUB -> /ground_station/formation_cmd] Commanded RETURN TO HOME (0, 0).")

    def _emergency_stop(self):
        for usv_id in self.usv_fleet:
            self.usv_fleet[usv_id]['status'] = 'ESTOP'
            self.usv_fleet[usv_id]['speed'] = 0.0

        self.emergency_stop_signal.emit(True)
        self.log_event("⚠ [PUB -> /ground_station/emergency_stop] EMERGENCY STOP TRIGGERED!")

    # --- Swarm Simulation Physics & Animation Loop ---
    def _tick(self):
        # Update Uptime
        elapsed = int(time.time() - self.start_time)
        mins, secs = divmod(elapsed, 60)
        self.uptime_label.setText(f"UPTIME: {mins:02d}:{secs:02d}")

        # Update Radar Sweep
        self.radar.update_animation()

        # Swarm Physics Simulation
        if self.simulation_enabled:
            targets = self.radar.formation_targets
            dt = 0.033  # seconds
            max_speed = 3.5  # m/s (~7 knots)
            max_turn_rate = 1.8  # rad/s

            for usv_id, data in self.usv_fleet.items():
                if data['status'] in ('FORMATION', 'RTH') and usv_id in targets:
                    tx = targets[usv_id]['x']
                    ty = targets[usv_id]['y']
                    dx = tx - data['x']
                    dy = ty - data['y']
                    dist = math.hypot(dx, dy)

                    if dist > 0.4:
                        desired_heading = math.atan2(dy, dx)
                        angle_diff = (desired_heading - data['heading'] + math.pi) % (2 * math.pi) - math.pi
                        turn = max(-max_turn_rate * dt, min(max_turn_rate * dt, angle_diff * 2.0))
                        data['heading'] += turn

                        # Speed slows down as approaching target
                        target_spd = min(max_speed, max(0.5, dist * 0.8))
                        data['speed'] = target_spd

                        data['x'] += math.cos(data['heading']) * data['speed'] * dt
                        data['y'] += math.sin(data['heading']) * data['speed'] * dt
                    else:
                        data['speed'] = 0.0

                    # Slight battery depletion
                    data['battery'] = max(0.0, data['battery'] - 0.002)

                self.radar.set_usv_state(usv_id, data['x'], data['y'], data['heading'], data['status'])

        # Update Fleet Table
        total_bat = 0.0
        sum_x, sum_y = 0.0, 0.0
        for row, (usv_id, data) in enumerate(self.usv_fleet.items()):
            total_bat += data['battery']
            sum_x += data['x']
            sum_y += data['y']

            if row < self.fleet_table.rowCount():
                self.fleet_table.item(row, 1).setText(f"{data['x']:.1f}, {data['y']:.1f}")
                self.fleet_table.item(row, 2).setText(f"{data['speed']:.1f} m/s")
                self.fleet_table.item(row, 3).setText(f"{int(data['battery'])}%")
                self.fleet_table.item(row, 4).setText(data['status'])

        n = max(1, len(self.usv_fleet))
        self.avg_bat_lbl.setText(f"{int(total_bat / n)}%")
        self.swarm_center_lbl.setText(f"({sum_x / n:.1f}m, {sum_y / n:.1f}m)")

    def log_event(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_console.append(f"<span style='color:#64748b;'>[{timestamp}]</span> {message}")
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())
