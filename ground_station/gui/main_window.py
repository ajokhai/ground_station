"""
HERMORD Ground Station Main Window.
Redesigned with Shadcn UI aesthetics:
- Neutral zinc color hierarchy
- Clean 1px borders and refined card elevations
- Minimalist typography and status pills
- Modern primary, secondary, and destructive button variants
"""

import sys
import math
import time
import json
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QSlider, QTableWidget,
    QTableWidgetItem, QHeaderView, QTextEdit, QGroupBox,
    QCheckBox, QFrame, QSplitter
)

from ground_station.gui.radar_widget import RadarWidget


SHADCN_STYLESHEET = """
QMainWindow {
    background-color: #09090b;
    color: #fafafa;
}
QWidget {
    font-family: -apple-system, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    color: #fafafa;
}

/* Card / Group Containers */
QGroupBox {
    border: 1px solid #27272a;
    border-radius: 8px;
    margin-top: 18px;
    padding-top: 14px;
    background-color: #121215;
    font-size: 12px;
    font-weight: 600;
    color: #a1a1aa;
    letter-spacing: 0.2px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 12px;
    color: #fafafa;
}

/* Table Widget */
QTableWidget {
    background-color: #0c0c0e;
    border: 1px solid #27272a;
    border-radius: 6px;
    gridline-color: #18181b;
    color: #f4f4f5;
    selection-background-color: #27272a;
    selection-color: #fafafa;
    font-size: 12px;
}
QHeaderView::section {
    background-color: #121215;
    color: #a1a1aa;
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid #27272a;
    font-weight: 500;
    font-size: 11px;
}

/* Buttons */
QPushButton {
    background-color: #18181b;
    color: #f4f4f5;
    border: 1px solid #27272a;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 500;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #27272a;
    border-color: #3f3f46;
}
QPushButton:pressed {
    background-color: #09090b;
}

/* Shadcn Primary Button (High-contrast clean white) */
QPushButton#primaryBtn {
    background-color: #fafafa;
    color: #09090b;
    border: 1px solid #ffffff;
    font-weight: 600;
}
QPushButton#primaryBtn:hover {
    background-color: #e4e4e7;
    border-color: #e4e4e7;
}
QPushButton#primaryBtn:pressed {
    background-color: #d4d4d8;
}

/* Shadcn Destructive Button */
QPushButton#destructiveBtn {
    background-color: #dc2626;
    color: #ffffff;
    border: 1px solid #ef4444;
    font-weight: 600;
}
QPushButton#destructiveBtn:hover {
    background-color: #b91c1c;
    border-color: #dc2626;
}
QPushButton#destructiveBtn:pressed {
    background-color: #991b1b;
}

/* Select / Dropdown */
QComboBox {
    background-color: #18181b;
    border: 1px solid #27272a;
    border-radius: 6px;
    padding: 6px 12px;
    color: #fafafa;
    font-size: 12px;
}
QComboBox:hover {
    border-color: #3f3f46;
}
QComboBox QAbstractItemView {
    background-color: #18181b;
    border: 1px solid #27272a;
    selection-background-color: #27272a;
    selection-color: #fafafa;
    color: #f4f4f5;
    padding: 4px;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 4px;
    background: #27272a;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #38bdf8;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #fafafa;
    border: 1px solid #71717a;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 7px;
}
QSlider::handle:horizontal:hover {
    background: #ffffff;
    border-color: #fafafa;
}

/* Checkbox */
QCheckBox {
    color: #a1a1aa;
    font-size: 12px;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border-radius: 4px;
    border: 1px solid #3f3f46;
    background-color: #18181b;
}
QCheckBox::indicator:checked {
    background-color: #fafafa;
    border-color: #fafafa;
}

/* Log Console */
QTextEdit {
    background-color: #0c0c0e;
    border: 1px solid #27272a;
    border-radius: 6px;
    color: #e4e4e7;
    font-family: Menlo, Monaco, monospace;
    font-size: 11px;
    padding: 6px;
}
"""


class MainWindow(QMainWindow):
    formation_command_signal = pyqtSignal(dict)
    emergency_stop_signal = pyqtSignal(bool)

    def __init__(self, ros_node=None):
        super().__init__()
        self.ros_node = ros_node
        self.setWindowTitle("HERMORD - Swarm Ground Station")
        self.resize(1200, 780)
        self.setStyleSheet(SHADCN_STYLESHEET)

        # Swarm State
        self.formation_center = {'x': 0.0, 'y': 0.0}
        self.formation_type = "V-Shape"
        self.formation_spacing = 15.0  # meters
        self.formation_heading = 90.0  # degrees
        self.simulation_enabled = True

        # Initialize USVs
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

        self.log_event("Ground Station initialized. Ready for swarm deployment.")

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 12, 14, 14)
        main_layout.setSpacing(10)

        # 1. Header Bar
        main_layout.addWidget(self._create_header_bar())

        # 2. Splitter Layout: Fleet List (Left) | Tactical Map (Center) | Mission Controls (Right)
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._create_fleet_panel())
        splitter.addWidget(self._create_map_panel())
        splitter.addWidget(self._create_control_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 5)
        splitter.setStretchFactor(2, 3)
        main_layout.addWidget(splitter, stretch=1)

        # 3. Bottom Log Console
        main_layout.addWidget(self._create_log_panel())

    def _create_header_bar(self):
        bar = QFrame()
        bar.setStyleSheet("background-color: #121215; border-radius: 8px; border: 1px solid #27272a; padding: 4px;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 8, 14, 8)

        # Title & Subtitle
        title_box = QHBoxLayout()
        title_label = QLabel("Ground Station")
        title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #fafafa;")
        title_box.addWidget(title_label)

        ver_badge = QLabel("v0.1.0")
        ver_badge.setStyleSheet("color: #71717a; font-size: 11px; padding: 2px 6px; background: #18181b; border-radius: 4px; border: 1px solid #27272a;")
        title_box.addWidget(ver_badge)

        sep = QLabel("/")
        sep.setStyleSheet("color: #3f3f46; font-size: 13px;")
        title_box.addWidget(sep)

        sub_label = QLabel("USV Swarm Formation Controller")
        sub_label.setStyleSheet("font-size: 12px; color: #a1a1aa; font-weight: 400;")
        title_box.addWidget(sub_label)

        layout.addLayout(title_box)
        layout.addStretch()

        # Status Pills
        self.ros_badge = QLabel("● ROS 2 Connected")
        self.ros_badge.setStyleSheet("color: #34d399; font-weight: 500; font-size: 11px; padding: 3px 10px; background: #064e3b; border-radius: 9999px; border: 1px solid #047857;")
        layout.addWidget(self.ros_badge)

        self.fleet_badge = QLabel("4 USVs Active")
        self.fleet_badge.setStyleSheet("color: #e4e4e7; font-weight: 500; font-size: 11px; padding: 3px 10px; background: #18181b; border-radius: 9999px; border: 1px solid #27272a;")
        layout.addWidget(self.fleet_badge)

        self.uptime_label = QLabel("00:00")
        self.uptime_label.setStyleSheet("color: #71717a; font-size: 11px; font-family: Menlo, monospace;")
        layout.addWidget(self.uptime_label)

        return bar

    def _create_fleet_panel(self):
        group = QGroupBox("Fleet Telemetry")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # Table of USVs
        self.fleet_table = QTableWidget(len(self.usv_fleet), 5)
        self.fleet_table.setHorizontalHeaderLabels(["Vehicle", "Position", "Speed", "Battery", "Status"])
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

        # Minimalist metrics row
        metrics_frame = QFrame()
        metrics_frame.setStyleSheet("background-color: #0c0c0e; border: 1px solid #27272a; border-radius: 6px; padding: 8px;")
        m_layout = QGridLayout(metrics_frame)
        m_layout.setContentsMargins(8, 6, 8, 6)

        m_layout.addWidget(QLabel("Fleet Battery:"), 0, 0)
        self.avg_bat_lbl = QLabel("89%")
        self.avg_bat_lbl.setStyleSheet("color: #34d399; font-weight: 600;")
        m_layout.addWidget(self.avg_bat_lbl, 0, 1)

        m_layout.addWidget(QLabel("Swarm Centroid:"), 1, 0)
        self.swarm_center_lbl = QLabel("(0.0m, 0.0m)")
        self.swarm_center_lbl.setStyleSheet("color: #a1a1aa; font-family: Menlo, monospace; font-size: 11px;")
        m_layout.addWidget(self.swarm_center_lbl, 1, 1)

        layout.addWidget(metrics_frame)

        # Fleet size selector
        size_layout = QHBoxLayout()
        size_lbl = QLabel("Swarm Size:")
        size_lbl.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        size_layout.addWidget(size_lbl)

        self.fleet_count_combo = QComboBox()
        self.fleet_count_combo.addItems(["2 USVs", "3 USVs", "4 USVs", "5 USVs", "6 USVs"])
        self.fleet_count_combo.setCurrentText("4 USVs")
        self.fleet_count_combo.currentTextChanged.connect(self._on_fleet_count_changed)
        size_layout.addWidget(self.fleet_count_combo)
        layout.addLayout(size_layout)

        return group

    def _create_map_panel(self):
        group = QGroupBox("Tactical Map Canvas")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Tactical Canvas (No rotating radar sweep)
        self.radar = RadarWidget()
        self.radar.waypoint_selected.connect(self._on_waypoint_selected)
        layout.addWidget(self.radar, stretch=1)

        # Clean Toolbar under map
        ctrl_bar = QHBoxLayout()
        reset_btn = QPushButton("Center View")
        reset_btn.clicked.connect(self.radar.reset_view)
        ctrl_bar.addWidget(reset_btn)

        zoom_in_btn = QPushButton("+ Zoom")
        zoom_in_btn.clicked.connect(lambda: setattr(self.radar, 'scale', min(50.0, self.radar.scale * 1.2)))
        ctrl_bar.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("- Zoom")
        zoom_out_btn.clicked.connect(lambda: setattr(self.radar, 'scale', max(2.0, self.radar.scale * 0.8)))
        ctrl_bar.addWidget(zoom_out_btn)

        ctrl_bar.addStretch()

        self.waypoint_lbl = QLabel("Target: (0.0, 0.0)m")
        self.waypoint_lbl.setStyleSheet("color: #38bdf8; font-family: Menlo, monospace; font-size: 11px; background: #18181b; padding: 4px 8px; border-radius: 4px; border: 1px solid #27272a;")
        ctrl_bar.addWidget(self.waypoint_lbl)

        layout.addLayout(ctrl_bar)
        return group

    def _create_control_panel(self):
        group = QGroupBox("Mission Controls")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Formation Geometry Selection
        geom_label = QLabel("Formation Pattern")
        geom_label.setStyleSheet("color: #a1a1aa; font-size: 12px; font-weight: 500;")
        layout.addWidget(geom_label)

        self.form_combo = QComboBox()
        self.form_combo.addItems(["V-Shape", "Line (Abeam)", "Column (In-line)", "Circle", "Diamond"])
        self.form_combo.currentTextChanged.connect(self._on_formation_type_changed)
        layout.addWidget(self.form_combo)

        # Spacing Slider
        spacing_header = QHBoxLayout()
        spacing_title = QLabel("Spacing")
        spacing_title.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        spacing_header.addWidget(spacing_title)
        spacing_header.addStretch()
        self.spacing_val_lbl = QLabel(f"{int(self.formation_spacing)} m")
        self.spacing_val_lbl.setStyleSheet("color: #fafafa; font-weight: 600; font-size: 11px; background: #18181b; padding: 2px 6px; border-radius: 4px; border: 1px solid #27272a;")
        spacing_header.addWidget(self.spacing_val_lbl)
        layout.addLayout(spacing_header)

        self.spacing_slider = QSlider(Qt.Horizontal)
        self.spacing_slider.setRange(5, 50)
        self.spacing_slider.setValue(int(self.formation_spacing))
        self.spacing_slider.valueChanged.connect(self._on_spacing_changed)
        layout.addWidget(self.spacing_slider)

        # Bearing Slider
        bearing_header = QHBoxLayout()
        bearing_title = QLabel("Bearing")
        bearing_title.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        bearing_header.addWidget(bearing_title)
        bearing_header.addStretch()
        self.heading_val_lbl = QLabel(f"{int(self.formation_heading)}°")
        self.heading_val_lbl.setStyleSheet("color: #fafafa; font-weight: 600; font-size: 11px; background: #18181b; padding: 2px 6px; border-radius: 4px; border: 1px solid #27272a;")
        bearing_header.addWidget(self.heading_val_lbl)
        layout.addLayout(bearing_header)

        self.heading_slider = QSlider(Qt.Horizontal)
        self.heading_slider.setRange(0, 359)
        self.heading_slider.setValue(int(self.formation_heading))
        self.heading_slider.valueChanged.connect(self._on_heading_changed)
        layout.addWidget(self.heading_slider)

        # Physics Simulation Toggle
        self.sim_checkbox = QCheckBox("Simulate Swarm Kinematics")
        self.sim_checkbox.setChecked(True)
        self.sim_checkbox.toggled.connect(lambda val: setattr(self, 'simulation_enabled', val))
        layout.addWidget(self.sim_checkbox)

        layout.addSpacing(6)

        # Primary Action Button
        self.deploy_btn = QPushButton("Deploy Formation")
        self.deploy_btn.setObjectName("primaryBtn")
        self.deploy_btn.setFixedHeight(36)
        self.deploy_btn.clicked.connect(self._deploy_formation)
        layout.addWidget(self.deploy_btn)

        # Secondary Action Buttons
        self.hold_btn = QPushButton("Hold Position")
        self.hold_btn.setFixedHeight(32)
        self.hold_btn.clicked.connect(self._hold_position)
        layout.addWidget(self.hold_btn)

        self.rth_btn = QPushButton("Return to Origin")
        self.rth_btn.setFixedHeight(32)
        self.rth_btn.clicked.connect(self._return_home)
        layout.addWidget(self.rth_btn)

        layout.addSpacing(10)

        # Destructive Action Button
        self.estop_btn = QPushButton("Emergency Stop")
        self.estop_btn.setObjectName("destructiveBtn")
        self.estop_btn.setFixedHeight(38)
        self.estop_btn.clicked.connect(self._emergency_stop)
        layout.addWidget(self.estop_btn)

        layout.addStretch()
        return group

    def _create_log_panel(self):
        group = QGroupBox("Activity & Telemetry Log")
        layout = QVBoxLayout(group)
        layout.setSpacing(4)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumHeight(110)
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
        fx = math.cos(bearing_rad)
        fy = math.sin(bearing_rad)
        rx = math.sin(bearing_rad)
        ry = -math.cos(bearing_rad)

        d = self.formation_spacing

        if self.formation_type == "V-Shape":
            for i, usv_id in enumerate(usv_ids):
                if i == 0:
                    targets[usv_id] = {'x': cx, 'y': cy}
                else:
                    tier = (i + 1) // 2
                    side = -1 if (i % 2 == 1) else 1
                    tx = cx - tier * d * fx + side * tier * d * rx
                    ty = cy - tier * d * fy + side * tier * d * ry
                    targets[usv_id] = {'x': tx, 'y': ty}

        elif self.formation_type == "Line (Abeam)":
            mid = (n - 1) / 2.0
            for i, usv_id in enumerate(usv_ids):
                offset = (i - mid) * d
                tx = cx + offset * rx
                ty = cy + offset * ry
                targets[usv_id] = {'x': tx, 'y': ty}

        elif self.formation_type == "Column (In-line)":
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
            positions = [(1, 0), (0, -1), (0, 1), (-1, 0)]
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
        self.log_event(f"Formation pattern changed to: {text}")

    def _on_spacing_changed(self, value):
        self.formation_spacing = float(value)
        self.spacing_val_lbl.setText(f"{value} m")
        self._calculate_formation_targets()

    def _on_heading_changed(self, value):
        self.formation_heading = float(value)
        self.heading_val_lbl.setText(f"{value}°")
        self._calculate_formation_targets()

    def _on_fleet_count_changed(self, text):
        count = int(text.split()[0])
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
        self.fleet_badge.setText(f"{count} USVs Active")
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
        self.log_event(f"Target destination updated to ({wx:.1f}m, {wy:.1f}m)")

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
        self.log_event(f"[PUB -> /ground_station/formation_cmd] Deployed {self.formation_type} ({len(targets)} vehicles)")

    def _hold_position(self):
        for usv_id in self.usv_fleet:
            self.usv_fleet[usv_id]['status'] = 'HOLD'
            self.usv_fleet[usv_id]['speed'] = 0.0

        cmd = {'action': 'HOLD', 'timestamp': time.time()}
        self.formation_command_signal.emit(cmd)
        self.log_event("[PUB -> /ground_station/formation_cmd] Commanded HOLD position.")

    def _return_home(self):
        self.formation_center = {'x': 0.0, 'y': 0.0}
        self.waypoint_lbl.setText("Target: (0.0, 0.0)m")
        self._calculate_formation_targets()
        for usv_id in self.usv_fleet:
            self.usv_fleet[usv_id]['status'] = 'RTH'

        cmd = {'action': 'RETURN_HOME', 'target': {'x': 0.0, 'y': 0.0}, 'timestamp': time.time()}
        self.formation_command_signal.emit(cmd)
        self.log_event("[PUB -> /ground_station/formation_cmd] Commanded RETURN TO ORIGIN.")

    def _emergency_stop(self):
        for usv_id in self.usv_fleet:
            self.usv_fleet[usv_id]['status'] = 'ESTOP'
            self.usv_fleet[usv_id]['speed'] = 0.0

        self.emergency_stop_signal.emit(True)
        self.log_event("⚠ [PUB -> /ground_station/emergency_stop] EMERGENCY STOP TRIGGERED!")

    # --- Swarm Kinematics Simulation ---
    def _tick(self):
        elapsed = int(time.time() - self.start_time)
        mins, secs = divmod(elapsed, 60)
        self.uptime_label.setText(f"{mins:02d}:{secs:02d}")

        self.radar.update_animation()

        if self.simulation_enabled:
            targets = self.radar.formation_targets
            dt = 0.033
            max_speed = 3.5
            max_turn_rate = 1.8

            for usv_id, data in self.usv_fleet.items():
                if data['status'] in ('FORMATION', 'RTH') and usv_id in targets:
                    tx = targets[usv_id]['x']
                    ty = targets[usv_id]['y']
                    dx = tx - data['x']
                    dy = ty - data['y']
                    dist = math.hypot(dx, dy)

                    if dist > 0.3:
                        desired_heading = math.atan2(dy, dx)
                        angle_diff = (desired_heading - data['heading'] + math.pi) % (2 * math.pi) - math.pi
                        turn = max(-max_turn_rate * dt, min(max_turn_rate * dt, angle_diff * 2.0))
                        data['heading'] += turn

                        target_spd = min(max_speed, max(0.4, dist * 0.8))
                        data['speed'] = target_spd

                        data['x'] += math.cos(data['heading']) * data['speed'] * dt
                        data['y'] += math.sin(data['heading']) * data['speed'] * dt
                    else:
                        data['speed'] = 0.0

                    data['battery'] = max(0.0, data['battery'] - 0.001)

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
        self.log_console.append(f"<span style='color:#71717a;'>[{timestamp}]</span> {message}")
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())
