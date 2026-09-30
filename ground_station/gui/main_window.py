"""
USV Ground Station — Main Window.
Coordinates GUI widgets, swarm state, kinematics simulation, manual teleoperation,
sensor telemetry streams, and ROS 2 dispatch.
"""

import sys
import math
import time
import random
from typing import Dict, Any, Optional, Set

from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFrame, QSplitter, QAction, QActionGroup
)

from ground_station.gui.theme import STYLESHEET
from ground_station.gui.formation_geometry import calculate_formation_targets
from ground_station.gui.radar_widget import RadarWidget
from ground_station.gui.toolbar import HeaderToolbar
from ground_station.gui.sidebar import SidebarWidget
from ground_station.gui.sensor_dialog import SensorDialog
from ground_station.gui.fleet_analytics_dialog import FleetAnalyticsDialog
from ground_station.gui.video_widget import VideoFeedWidget
from ground_station.gui.help_dialog import HelpGuideDialog
from ground_station.gui.datum_dialog import MaritimeDatumDialog, MARITIME_PRESETS
from ground_station.core.georeference import point_in_polygon, dist_to_segment


class MainWindow(QMainWindow):
    formation_command_signal = pyqtSignal(dict)
    emergency_stop_signal = pyqtSignal(bool)
    geofence_broadcast_signal = pyqtSignal(dict)
    usv_target_pose_signal = pyqtSignal(str, float, float, float)  # (usv_id, x, y, heading_rad)
    usv_autonomy_mode_signal = pyqtSignal(str, str)                # (usv_id, mode)
    usv_cmd_vel_signal = pyqtSignal(str, float, float)              # (usv_id, linear_x, angular_z)

    def __init__(self, ros_node=None):
        super().__init__()
        self.ros_node = ros_node
        self.setWindowTitle("USV Ground Station")
        self.setMinimumSize(960, 620)
        self.resize(1120, 720)
        self.setStyleSheet(STYLESHEET)

        # ─── State ───
        self.operation_mode = "SIMULATION"  # "SIMULATION" vs "EXTERNAL"
        self.formation_center = {'x': 0.0, 'y': 0.0}
        self.formation_type = "V-Shape"
        self.formation_spacing = 15.0
        self.formation_heading = 90.0
        self.simulation_enabled = True
        self.selected_usv: Optional[str] = None

        # Manual drive teleop state
        self.manual_drive_enabled = False
        self.keys_pressed: Set[int] = set()
        self.active_sensor_dialog: Optional[SensorDialog] = None
        self.active_fleet_dialog: Optional[FleetAnalyticsDialog] = None
        self.active_help_dialog: Optional[HelpGuideDialog] = None

        self.usv_fleet: Dict[str, Dict[str, Any]] = {
            'USV-1': {
                'x': -15.0, 'y': -15.0, 'heading': 0.0, 'speed': 0.0,
                'battery': 94.0, 'signal': 96.0, 'rssi': -62,
                'status': 'IDLE', 'custom_target': None, 'yaw_rate': 0.0,
                'pitch': 1.2, 'roll': -0.8,
                'met_data': {
                    'wind_spd': 14.2, 'wind_dir': 48.0, 'wind_gust': 18.5,
                    'current_spd': 1.2, 'current_dir': 62.0, 'depth': 18.2,
                    'water_temp': 16.8, 'barometer': 1012.8, 'sensor': 'Airmar 200WX Ultrasonic'
                }
            },
            'USV-2': {
                'x': -10.0, 'y': -25.0, 'heading': 0.0, 'speed': 0.0,
                'battery': 88.0, 'signal': 93.0, 'rssi': -65,
                'status': 'IDLE', 'custom_target': None, 'yaw_rate': 0.0,
                'pitch': 0.8, 'roll': 0.5,
                'met_data': {
                    'wind_spd': 13.8, 'wind_dir': 46.0, 'wind_gust': 17.9,
                    'current_spd': 1.1, 'current_dir': 59.0, 'depth': 19.1,
                    'water_temp': 16.9, 'barometer': 1013.0, 'sensor': 'Airmar 200WX Ultrasonic'
                }
            },
            'USV-3': {
                'x':  10.0, 'y': -25.0, 'heading': 0.0, 'speed': 0.0,
                'battery': 91.0, 'signal': 97.0, 'rssi': -60,
                'status': 'IDLE', 'custom_target': None, 'yaw_rate': 0.0,
                'pitch': 1.4, 'roll': -1.1,
                'met_data': {
                    'wind_spd': 12.1, 'wind_dir': 40.0, 'wind_gust': 15.6,
                    'current_spd': 0.9, 'current_dir': 54.0, 'depth': 21.0,
                    'water_temp': 17.1, 'barometer': 1013.6, 'sensor': 'Airmar 200WX Ultrasonic'
                }
            },
            'USV-4': {
                'x':  15.0, 'y': -15.0, 'heading': 0.0, 'speed': 0.0,
                'battery': 85.0, 'signal': 90.0, 'rssi': -68,
                'status': 'IDLE', 'custom_target': None, 'yaw_rate': 0.0,
                'pitch': 0.9, 'roll': 0.7,
                'met_data': {
                    'wind_spd': 14.9, 'wind_dir': 52.0, 'wind_gust': 19.2,
                    'current_spd': 1.3, 'current_dir': 66.0, 'depth': 17.8,
                    'water_temp': 16.7, 'barometer': 1012.4, 'sensor': 'Airmar 200WX Ultrasonic'
                }
            },
        }

        self.start_time = time.time()

        # Regional Weather Report (NOAA / Met Station Forecast)
        self.weather_report = {
            'wind_spd': 11.4,
            'wind_dir': 35.0,
            'wind_gust': 14.8,
            'current_spd': 0.8,
            'current_dir': 50.0,
            'depth': 18.5,
            'tide': '+0.4m',
            'sea_state': 'State 2 (0.3m)',
            'water_temp': 17.2,
            'barometer': 1014.2,
            'gps_fix': 'RTK Fixed (3D)',
            'lat_str': '37°46\'N',
            'lon_str': '122°25\'W',
            'sats': 19,
            'hdop': 0.65,
            'station': 'NOAA Station #46026',
        }
        self.env_data = self.weather_report

        # ─── Build UI Components ───
        self._init_menu_bar()
        self._init_ui()
        self._init_status_bar()

        # Initial data sync
        self.sidebar.populate_fleet_table(self.usv_fleet)
        self.sidebar.set_swarm_size(len(self.usv_fleet))
        self._calculate_targets()
        self._deselect_usv()  # Start in clean Fleet Overview mode

        drone_mets = {uid: d.get('met_data', {}) for uid, d in self.usv_fleet.items()}
        self.sidebar.update_metocean_data(self.weather_report, drone_mets)
        self.radar.set_metocean_data(self.weather_report, self.usv_fleet['USV-1'].get('met_data'))
        self._reposition_video_pip()

        # Hazard obstacles list (clean by default; populated via user placement or ROS 2)
        self.radar.set_obstacles([])

        # 30 Hz animation/telemetry tick
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._tick)
        self.anim_timer.start(33)

        self.log_event("System initialized and ready.")

    # ─── MENU BAR ─────────────────────────────────────────────────────────────

    def _init_menu_bar(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("File")
        file_menu.addAction("New Mission")
        file_menu.addAction("Save Mission Log...")
        file_menu.addSeparator()
        close_act = QAction("Close Window", self)
        close_act.setShortcut(QKeySequence("Ctrl+W"))
        close_act.triggered.connect(self.close)
        file_menu.addAction(close_act)

        # Mission
        mission_menu = mb.addMenu("Mission")

        deploy_act = QAction("Deploy Formation", self)
        deploy_act.setShortcut(QKeySequence("Ctrl+D"))
        deploy_act.triggered.connect(self._deploy_formation)
        mission_menu.addAction(deploy_act)

        hold_act = QAction("Hold Position", self)
        hold_act.setShortcut(QKeySequence("Ctrl+H"))
        hold_act.triggered.connect(self._hold_position)
        mission_menu.addAction(hold_act)

        rth_act = QAction("Return to Origin", self)
        rth_act.setShortcut(QKeySequence("Ctrl+R"))
        rth_act.triggered.connect(self._return_home)
        mission_menu.addAction(rth_act)

        mission_menu.addSeparator()

        estop_act = QAction("Emergency Stop", self)
        estop_act.setShortcut(QKeySequence("Ctrl+E"))
        estop_act.triggered.connect(self._emergency_stop)
        mission_menu.addAction(estop_act)

        mission_menu.addSeparator()

        reset_act = QAction("Reset Target to Origin (0, 0)", self)
        reset_act.triggered.connect(lambda: self._on_waypoint_selected(0.0, 0.0))
        mission_menu.addAction(reset_act)

        clear_obs_act = QAction("Clear All Hazards", self)
        clear_obs_act.triggered.connect(self._clear_all_obstacles)
        mission_menu.addAction(clear_obs_act)

        mission_menu.addSeparator()
        jump_datum_act = QAction("Maritime Operational Area (GPS Datum)...", self)
        jump_datum_act.setShortcut(QKeySequence("Ctrl+Shift+D"))
        jump_datum_act.triggered.connect(self._open_custom_datum_dialog)
        mission_menu.addAction(jump_datum_act)

        # Fleet
        fleet_menu = mb.addMenu("Fleet")
        size_menu = fleet_menu.addMenu("Swarm Size")
        self.size_action_group = QActionGroup(self)
        for count in [2, 3, 4, 5, 6, 8]:
            act = QAction(f"{count} USVs", self, checkable=True)
            if count == 4:
                act.setChecked(True)
            act.triggered.connect(lambda checked, c=count: self._on_fleet_count_changed(c))
            self.size_action_group.addAction(act)
            size_menu.addAction(act)

        fleet_menu.addSeparator()

        self.sim_action = QAction("Enable Kinematics Simulation", self, checkable=True)
        self.sim_action.setChecked(True)
        self.sim_action.toggled.connect(lambda val: setattr(self, 'simulation_enabled', val))
        fleet_menu.addAction(self.sim_action)

        # View
        view_menu = mb.addMenu("View")

        self.style_menu = view_menu.addMenu("Map Style")
        self.style_group = QActionGroup(self)
        for style_name in ["Grid", "Tactical", "Satellite", "Nautical Chart", "Minimal"]:
            act = QAction(style_name, self, checkable=True)
            if style_name == "Grid":
                act.setChecked(True)
            act.triggered.connect(lambda checked, s=style_name: self._on_view_mode_changed(s))
            self.style_group.addAction(act)
            self.style_menu.addAction(act)

        self.marine_area_menu = view_menu.addMenu("Maritime Operations Area")
        for p in MARITIME_PRESETS:
            act = QAction(f"{p['name']} ({p['region']})", self)
            act.triggered.connect(lambda checked, name=p['name'], lat=p['lat'], lon=p['lon']: self._set_maritime_operational_area(name, lat, lon))
            self.marine_area_menu.addAction(act)
        self.marine_area_menu.addSeparator()
        custom_datum_act = QAction("Custom GPS Datum Coordinates...", self)
        custom_datum_act.triggered.connect(self._open_custom_datum_dialog)
        self.marine_area_menu.addAction(custom_datum_act)

        view_menu.addSeparator()

        self.toggle_sidebar_action = QAction("Show Sidebar", self, checkable=True)
        self.toggle_sidebar_action.setChecked(True)
        self.toggle_sidebar_action.setShortcut(QKeySequence("Ctrl+1"))
        self.toggle_sidebar_action.toggled.connect(self._toggle_sidebar)
        view_menu.addAction(self.toggle_sidebar_action)

        self.toggle_video_action = QAction("Show Live Video Feed", self, checkable=True)
        self.toggle_video_action.setChecked(False)
        self.toggle_video_action.setShortcut(QKeySequence("Ctrl+V"))
        self.toggle_video_action.toggled.connect(self._toggle_video_feed)
        view_menu.addAction(self.toggle_video_action)

        self.toggle_console_action = QAction("Show Console", self, checkable=True)
        self.toggle_console_action.setChecked(False)
        self.toggle_console_action.setShortcut(QKeySequence("Ctrl+`"))
        self.toggle_console_action.toggled.connect(self._toggle_console)
        view_menu.addAction(self.toggle_console_action)

        fleet_diag_act = QAction("Swarm Fleet Analytics...", self)
        fleet_diag_act.setShortcut(QKeySequence("Ctrl+Shift+A"))
        fleet_diag_act.triggered.connect(self._open_fleet_analytics_dialog)
        view_menu.addAction(fleet_diag_act)

        view_menu.addSeparator()

        center_act = QAction("Center on Origin", self)
        center_act.setShortcut(QKeySequence("Ctrl+0"))
        center_act.triggered.connect(lambda: self.radar.reset_view())
        view_menu.addAction(center_act)

        zoom_in_act = QAction("Zoom In", self)
        zoom_in_act.setShortcut(QKeySequence("Ctrl+="))
        zoom_in_act.triggered.connect(lambda: setattr(self.radar, 'scale', min(50.0, self.radar.scale * 1.25)))
        view_menu.addAction(zoom_in_act)

        zoom_out_act = QAction("Zoom Out", self)
        zoom_out_act.setShortcut(QKeySequence("Ctrl+-"))
        zoom_out_act.triggered.connect(lambda: setattr(self.radar, 'scale', max(2.0, self.radar.scale * 0.8)))
        view_menu.addAction(zoom_out_act)

        # Help
        help_menu = mb.addMenu("Help")

        user_guide_act = QAction("User Guide & Documentation...", self)
        user_guide_act.setShortcut(QKeySequence("F1"))
        user_guide_act.triggered.connect(lambda: self._open_help_dialog("getting_started"))
        help_menu.addAction(user_guide_act)

        shortcuts_act = QAction("Keyboard Shortcuts Reference...", self)
        shortcuts_act.setShortcut(QKeySequence("Ctrl+/"))
        shortcuts_act.triggered.connect(lambda: self._open_help_dialog("shortcuts"))
        help_menu.addAction(shortcuts_act)

        ros2_ref_act = QAction("ROS 2 Topic Architecture...", self)
        ros2_ref_act.triggered.connect(lambda: self._open_help_dialog("ros2_architecture"))
        help_menu.addAction(ros2_ref_act)

        help_menu.addSeparator()

        about_act = QAction("About USV Ground Station...", self)
        about_act.triggered.connect(self._open_about_dialog)
        help_menu.addAction(about_act)

    # ─── UI LAYOUT ────────────────────────────────────────────────────────────

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Toolbar ──
        self.toolbar = HeaderToolbar()
        self.toolbar.deploy_clicked.connect(self._deploy_formation)
        self.toolbar.hold_clicked.connect(self._hold_position)
        self.toolbar.return_home_clicked.connect(self._return_home)
        self.toolbar.view_mode_changed.connect(self._on_view_mode_changed)
        self.toolbar.operation_mode_changed.connect(self.set_operation_mode)
        self.toolbar.emergency_stop_clicked.connect(self._emergency_stop)
        self.toolbar.sidebar_toggle_clicked.connect(self._toggle_sidebar)
        self.toolbar.video_toggle_clicked.connect(self._toggle_video_feed)
        root.addWidget(self.toolbar)

        # ── Manual Drive HUD Banner (shown when driving) ──
        self.manual_banner = QFrame()
        self.manual_banner.setFixedHeight(30)
        self.manual_banner.setStyleSheet("""
            QFrame {
                background: #451a03;
                border-bottom: 1px solid #b45309;
            }
        """)
        mb_layout = QHBoxLayout(self.manual_banner)
        mb_layout.setContentsMargins(14, 0, 14, 0)
        self.manual_banner_label = QLabel()
        self.manual_banner_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #fef3c7;")
        mb_layout.addWidget(self.manual_banner_label)
        mb_layout.addStretch()

        exit_drive_btn = QPushButton("✕ Exit Drive (Esc)")
        exit_drive_btn.setFixedHeight(20)
        exit_drive_btn.setStyleSheet("""
            QPushButton {
                background: #78350f;
                border: 1px solid #f59e0b;
                border-radius: 3px;
                color: #ffffff;
                font-size: 10px;
                font-weight: 600;
                padding: 0 8px;
            }
            QPushButton:hover {
                background: #92400e;
            }
        """)
        exit_drive_btn.clicked.connect(lambda: self._toggle_manual_drive(force_off=True))
        mb_layout.addWidget(exit_drive_btn)
        self.manual_banner.setVisible(False)
        root.addWidget(self.manual_banner)

        # ── Resizable Splitter: Radar Canvas + Sidebar ──
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)

        self.radar = RadarWidget()
        self.radar.waypoint_selected.connect(self._on_waypoint_selected)
        self.radar.individual_waypoint_selected.connect(self._on_individual_waypoint_selected)
        self.radar.usv_selected.connect(self._on_radar_usv_selected)
        self.radar.cursor_coordinate_changed.connect(self._on_radar_cursor_moved)
        self.radar.obstacle_added.connect(self._on_obstacle_added)
        self.radar.obstacle_removed.connect(self._on_obstacle_removed)
        self.radar.obstacle_moved.connect(self._on_obstacle_moved)
        self.radar.geofence_added.connect(self._on_geofence_added)
        self.radar.geofence_removed.connect(self._on_geofence_removed)
        self.radar.datum_changed.connect(self._on_datum_changed)

        self.splitter.addWidget(self.radar)

        self.sidebar = SidebarWidget()
        self.sidebar.formation_type_changed.connect(self._on_formation_type_changed)
        self.sidebar.formation_spacing_changed.connect(self._on_formation_spacing_changed)
        self.sidebar.formation_heading_changed.connect(self._on_formation_heading_changed)
        self.sidebar.deploy_clicked.connect(self._deploy_formation)
        self.sidebar.swarm_size_changed.connect(self._on_fleet_count_changed)
        self.sidebar.usv_selected.connect(self._select_usv)
        self.sidebar.deselect_clicked.connect(self._deselect_usv)
        self.sidebar.focus_usv_clicked.connect(self._focus_usv)
        self.sidebar.hold_usv_clicked.connect(self._hold_single_usv)
        self.sidebar.rejoin_formation_clicked.connect(self._on_rejoin_formation)
        self.sidebar.manual_drive_clicked.connect(self._toggle_manual_drive)
        self.sidebar.view_sensors_clicked.connect(self._open_sensor_dialog)
        self.sidebar.view_fleet_analytics_clicked.connect(self._open_fleet_analytics_dialog)
        self.splitter.addWidget(self.sidebar)

        self.splitter.setSizes([820, 300])
        root.addWidget(self.splitter, stretch=1)

        # ── Picture-in-Picture Live Video Feed (Overlaid on Radar Canvas) ──
        self.video_pip = VideoFeedWidget(parent=self.radar)
        self.video_pip.swap_view_requested.connect(self._toggle_video_expanded)
        self.video_pip.detach_requested.connect(self._toggle_video_detached)
        self.video_pip.close_requested.connect(lambda: self._toggle_video_feed(False))
        self.radar.resized.connect(self._reposition_video_pip)
        self.video_pip.hide()

        # ── Collapsible Console ──
        self.console_container = self._create_console()
        self.console_container.setVisible(False)
        root.addWidget(self.console_container)

    def _create_console(self) -> QFrame:
        container = QFrame()
        container.setMaximumHeight(100)
        container.setStyleSheet("background: #09090b; border-top: 1px solid #1c1c1f;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(0)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        layout.addWidget(self.log_console)
        return container

    def _init_status_bar(self):
        sb = self.statusBar()
        sb.setSizeGripEnabled(False)
        sb.setStyleSheet("QStatusBar { background: #09090b; border-top: 1px solid #1c1c1f; } QStatusBar::item { border: none; }")

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(0)

        self.st_conn = QLabel("● Connected")
        self.st_conn.setStyleSheet("color: #34d399; font-size: 10px;")
        layout.addWidget(self.st_conn)

        layout.addWidget(self._st_sep())

        self.st_mode = QLabel("🎮 SIMULATION")
        self.st_mode.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 700;")
        layout.addWidget(self.st_mode)

        layout.addWidget(self._st_sep())

        self.st_cursor = QLabel("Cursor: 37°46'29.6\"N  122°25'09.8\"W (0.0m, 0.0m)")
        self.st_cursor.setStyleSheet("color: #a1a1aa; font-family: Menlo, monospace; font-size: 10px;")
        layout.addWidget(self.st_cursor)

        layout.addWidget(self._st_sep())

        self.st_target = QLabel("Target: (0.0, 0.0)")
        self.st_target.setStyleSheet("color: #38bdf8; font-family: Menlo, monospace; font-size: 10px;")
        layout.addWidget(self.st_target)

        layout.addStretch()

        self.st_teleop = QLabel("")
        self.st_teleop.setStyleSheet("color: #fbbf24; font-size: 10px; font-weight: 600; padding-right: 12px;")
        layout.addWidget(self.st_teleop)

        self.st_network = QLabel("📶 -62 dBm · ↓ 18.4M ↑ 3.2M · 8ms")
        self.st_network.setStyleSheet("color: #34d399; font-family: Menlo, monospace; font-size: 10px; font-weight: 600; padding-right: 10px;")
        layout.addWidget(self.st_network)

        layout.addWidget(self._st_sep())

        self.st_fleet = QLabel("4 USVs")
        self.st_fleet.setStyleSheet("color: #71717a; font-size: 10px;")
        layout.addWidget(self.st_fleet)

        layout.addWidget(self._st_sep())

        self.st_uptime = QLabel("00:00")
        self.st_uptime.setStyleSheet("color: #52525b; font-family: Menlo, monospace; font-size: 10px;")
        layout.addWidget(self.st_uptime)

        sb.addPermanentWidget(container, 1)

    def _st_sep(self) -> QLabel:
        lbl = QLabel("  ·  ")
        lbl.setStyleSheet("color: #27272a; font-size: 10px;")
        return lbl

    # ─── FORMATION GEOMETRY COORDINATION ──────────────────────────────────────

    def _calculate_targets(self):
        targets = calculate_formation_targets(
            formation_type=self.formation_type,
            center_x=self.formation_center['x'],
            center_y=self.formation_center['y'],
            heading_deg=self.formation_heading,
            spacing=self.formation_spacing,
            usv_ids=list(self.usv_fleet.keys())
        )
        self.radar.set_formation_targets(targets, name=self.formation_type)
        return targets

    # ─── SLOTS & EVENTS ───────────────────────────────────────────────────────

    def _on_formation_type_changed(self, text: str):
        self.formation_type = text
        self._calculate_targets()
        for uid, d in self.usv_fleet.items():
            if d['status'] in ('AVOIDING', 'HOLD', 'IDLE') and not d.get('custom_target'):
                d['status'] = 'FORMATION'
        self.log_event(f"Formation changed to {text}")

    def _on_formation_spacing_changed(self, val: float):
        self.formation_spacing = val
        self._calculate_targets()
        for uid, d in self.usv_fleet.items():
            if d['status'] in ('AVOIDING', 'HOLD') and not d.get('custom_target'):
                d['status'] = 'FORMATION'

    def _on_formation_heading_changed(self, val: float):
        self.formation_heading = val
        self._calculate_targets()
        for uid, d in self.usv_fleet.items():
            if d['status'] in ('AVOIDING', 'HOLD') and not d.get('custom_target'):
                d['status'] = 'FORMATION'

    def _on_view_mode_changed(self, text: str):
        self.radar.set_view_mode(text)
        self.toolbar.set_view_mode(text)
        for act in self.style_group.actions():
            if act.text() == text:
                act.setChecked(True)
                break

    def _on_fleet_count_changed(self, count: int):
        new_fleet = {}
        for i in range(1, count + 1):
            uid = f"USV-{i}"
            if uid in self.usv_fleet:
                new_fleet[uid] = self.usv_fleet[uid]
            else:
                new_fleet[uid] = {
                    'x': -10.0 * i, 'y': -20.0,
                    'heading': 0.0, 'speed': 0.0,
                    'battery': 95.0, 'signal': 95.0, 'rssi': -63,
                    'status': 'IDLE', 'custom_target': None, 'yaw_rate': 0.0,
                    'pitch': 1.0, 'roll': 0.0,
                    'met_data': {
                        'wind_spd': 12.0 + (i * 0.7),
                        'wind_dir': (35 + i * 4) % 360,
                        'wind_gust': 15.0 + (i * 0.9),
                        'current_spd': 0.8 + (i * 0.1),
                        'current_dir': (50 + i * 3) % 360,
                        'depth': 18.0 + (i * 0.5),
                        'water_temp': 17.0 - (i * 0.1),
                        'barometer': 1014.0 - (i * 0.3),
                        'sensor': 'Airmar 200WX Ultrasonic'
                    }
                }
        self.usv_fleet = new_fleet
        self.radar.usvs.clear()
        self.st_fleet.setText(f"{count} USVs")
        self.sidebar.set_swarm_size(count)
        self.sidebar.populate_fleet_table(self.usv_fleet)

        # Sync menu action
        for act in self.size_action_group.actions():
            if act.text().startswith(str(count)):
                act.setChecked(True)
                break

        self._calculate_targets()
        if self.selected_usv and self.selected_usv not in self.usv_fleet:
            self._deselect_usv()
        elif self.selected_usv is None:
            self.sidebar.show_fleet_overview(self.usv_fleet, self.formation_type, self.formation_center)

        self.log_event(f"Fleet updated to {count} vehicles")

    def _on_radar_usv_selected(self, usv_id: str):
        if not usv_id:
            self._deselect_usv()
        else:
            self._select_usv(usv_id)

    def _select_usv(self, usv_id: str):
        if usv_id not in self.usv_fleet:
            return
        self.selected_usv = usv_id
        self.radar.selected_usv = usv_id
        self.radar.update()
        self.sidebar.select_usv(usv_id)
        self.sidebar.update_inspector(usv_id, self.usv_fleet[usv_id])
        if hasattr(self, 'video_pip'):
            self.video_pip.set_usv(usv_id)
            if 'camera_frame' in self.usv_fleet[usv_id]:
                self.video_pip.set_camera_frame(self.usv_fleet[usv_id]['camera_frame'])
            else:
                self.video_pip.external_frame = None
        if hasattr(self, 'radar') and 'met_data' in self.usv_fleet[usv_id]:
            self.radar.set_metocean_data(self.weather_report, self.usv_fleet[usv_id]['met_data'])

    def _deselect_usv(self):
        """Unselect single drone and show Fleet Overview."""
        if self.manual_drive_enabled:
            self._toggle_manual_drive(force_off=True)
        self.selected_usv = None
        self.radar.selected_usv = None
        self.radar.update()
        self.sidebar.select_usv(None)
        self.sidebar.show_fleet_overview(self.usv_fleet, self.formation_type, self.formation_center)
        if hasattr(self, 'video_pip'):
            self.video_pip.set_usv("USV-1")
        if hasattr(self, 'radar') and hasattr(self, 'weather_report'):
            first_met = self.usv_fleet.get('USV-1', {}).get('met_data')
            self.radar.set_metocean_data(self.weather_report, first_met)

    def _focus_usv(self, usv_id: str):
        if usv_id in self.usv_fleet:
            self.radar.focus_usv(usv_id)

    def _hold_single_usv(self, usv_id: str):
        if usv_id in self.usv_fleet:
            self.usv_fleet[usv_id]['status'] = 'HOLD'
            self.usv_fleet[usv_id]['speed'] = 0.0
            self.log_event(f"Hold commanded for {usv_id}")
            self.sidebar.update_inspector(usv_id, self.usv_fleet[usv_id])
            self.usv_autonomy_mode_signal.emit(usv_id, 'HOLD')

    def _on_individual_waypoint_selected(self, usv_id: str, wx: float, wy: float):
        """Arbitrarily select a drone and change its target position."""
        if usv_id not in self.usv_fleet:
            return
        self.usv_fleet[usv_id]['custom_target'] = {'x': wx, 'y': wy}
        self.radar.custom_targets[usv_id] = {'x': wx, 'y': wy}
        self.usv_fleet[usv_id]['status'] = 'TRANSIT'
        self.radar.update()
        self.sidebar.update_inspector(usv_id, self.usv_fleet[usv_id])
        self.log_event(f"{usv_id}: Individual waypoint assigned to ({wx:.1f}, {wy:.1f})")
        self.usv_target_pose_signal.emit(usv_id, float(wx), float(wy), math.radians(self.formation_heading))
        self.usv_autonomy_mode_signal.emit(usv_id, 'TRANSIT')

    def _on_rejoin_formation(self, usv_id: str):
        """Cancel individual waypoint and return to formation slot."""
        if usv_id in self.usv_fleet:
            self.usv_fleet[usv_id]['custom_target'] = None
            self.radar.custom_targets.pop(usv_id, None)
            self.usv_fleet[usv_id]['status'] = 'FORMATION'
            self.radar.update()
            self.sidebar.update_inspector(usv_id, self.usv_fleet[usv_id])
            self.log_event(f"{usv_id}: Rejoining {self.formation_type} formation")
            self.usv_autonomy_mode_signal.emit(usv_id, 'FORMATION')


    def _on_radar_cursor_moved(self, wx: float, wy: float, lat: float, lon: float):
        if hasattr(self, 'st_cursor'):
            dms = self.radar.georef.format_dms(lat, lon)
            self.st_cursor.setText(f"Cursor: {dms} ({wx:+.1f}m, {wy:+.1f}m)")

    def _on_obstacle_added(self, obs: dict):
        self.log_event(f"➕ Hazard added: {obs.get('label')} at ({obs.get('x'):.1f}m, {obs.get('y'):.1f}m) [{obs.get('source', 'Manual')}]")

    def _on_obstacle_removed(self, obs: dict):
        self.log_event(f"🗑️ Hazard removed: {obs.get('label')}")

    def _on_obstacle_moved(self, obs: dict):
        self.log_event(f"↔️ Hazard repositioned: {obs.get('label')} at ({obs.get('x'):.1f}m, {obs.get('y'):.1f}m)")

    def _clear_all_obstacles(self):
        self.radar.clear_obstacles()
        self.log_event("🗑️ All marine hazard obstacles cleared.")

    def _on_datum_changed(self, lat: float, lon: float):
        self.log_event(f"⚓ Datum Reference updated to {lat:.6f}°N, {abs(lon):.6f}°W")

    def _set_maritime_operational_area(self, name: str, lat: float, lon: float):
        self.radar.set_datum(lat, lon)
        self.radar.reset_view()
        self.log_event(f"⚓ Maritime operational area relocated to: {name} [{lat:.4f}°N, {abs(lon):.4f}°W]")
        if hasattr(self, 'weather_report'):
            self.weather_report['lat_str'] = f"{abs(lat):.2f}°{'N' if lat >= 0 else 'S'}"
            self.weather_report['lon_str'] = f"{abs(lon):.2f}°{'E' if lon >= 0 else 'W'}"
            self.weather_report['station'] = f"Operational Zone ({name})"

    def _open_custom_datum_dialog(self):
        current_lat = self.radar.georef.datum_lat
        current_lon = self.radar.georef.datum_lon
        dlg = MaritimeDatumDialog(current_lat, current_lon, parent=self)
        dlg.datum_selected.connect(self._set_maritime_operational_area)
        dlg.exec_()

    def _on_geofence_added(self, gf: dict):
        name = gf.get('name', 'ZONE')
        pts_count = len(gf.get('points', []))
        self.log_event(f"🛑 Geofence active: {name} ({pts_count} vertices). Broadcasting to fleet...")
        self.geofence_broadcast_signal.emit(gf)

    def _on_geofence_removed(self, gf: dict):
        name = gf.get('name', 'ZONE')
        self.log_event(f"🗑️ Geofence removed: {name}")
        gf_del = dict(gf)
        gf_del['points'] = []
        gf_del['action'] = 'DELETE'
        self.geofence_broadcast_signal.emit(gf_del)


    def ingest_external_obstacle(self, data):
        """Called when ROS 2 receives obstacle detections from real USVs or external simulators."""
        if isinstance(data, list):
            for item in data:
                self._ingest_single_obstacle(item)
        elif isinstance(data, dict):
            self._ingest_single_obstacle(data)

    def _ingest_single_obstacle(self, item: dict):
        source = item.get('source', 'USV')
        x = float(item.get('x', 0.0))
        y = float(item.get('y', 0.0))
        radius = float(item.get('radius', 5.0))
        label = str(item.get('label', 'HAZARD'))
        level = str(item.get('level', 'hazard'))
        self.radar.ingest_detected_obstacle(source, x, y, radius, label, level)
        self.log_event(f"📡 Real-time Detection: {label} [{source}] at ({x:+.1f}m, {y:+.1f}m)")

    def _on_waypoint_selected(self, wx: float, wy: float):
        self.formation_center = {'x': wx, 'y': wy}
        latlon = self.radar.georef.to_latlon(wx, wy)
        self.st_target.setText(f"Target: ({wx:+.1f}m, {wy:+.1f}m) · {latlon.lat:.4f}°N, {abs(latlon.lon):.4f}°W")
        self._calculate_targets()
        for uid, d in self.usv_fleet.items():
            if d['status'] in ('AVOIDING', 'HOLD', 'IDLE') and not d.get('custom_target'):
                d['status'] = 'FORMATION'
        if self.selected_usv is None:
            self.sidebar.show_fleet_overview(self.usv_fleet, self.formation_type, self.formation_center)
        self.log_event(f"Target anchor updated to ({wx:+.1f}m, {wy:+.1f}m) [{latlon.lat:.4f}°N, {abs(latlon.lon):.4f}°W]")

    # ─── SIMULATION & EXTERNAL ROS 2 BRIDGE INGESTION ─────────────────────────

    def set_operation_mode(self, mode: str):
        """Switch between internal kinematics simulation and live external ROS 2 / Hardware mode."""
        if hasattr(self, 'operation_mode') and self.operation_mode == mode and hasattr(self, 'st_mode') and mode in self.st_mode.text():
            return
        self.operation_mode = mode
        if hasattr(self, 'toolbar'):
            self.toolbar.set_operation_mode(mode)
        if hasattr(self, 'st_mode'):
            if mode == "EXTERNAL":
                self.st_mode.setText("📡 EXTERNAL ROS 2")
                self.st_mode.setStyleSheet("color: #34d399; font-size: 10px; font-weight: 700;")
            else:
                self.st_mode.setText("🎮 SIMULATION")
                self.st_mode.setStyleSheet("color: #38bdf8; font-size: 10px; font-weight: 700;")
        if mode == "EXTERNAL":
            self.log_event("📡 Mode: EXTERNAL ROS 2 active. Ingesting live vehicle telemetry; internal physics paused.")
        else:
            self.log_event("🎮 Mode: STANDALONE SIMULATION active. Internal kinematics model running.")

    def register_external_usv(self, usv_id: str):
        """Dynamically register an external USV discovered on the ROS 2 graph."""
        if usv_id not in self.usv_fleet:
            self.usv_fleet[usv_id] = {
                'x': 0.0, 'y': 0.0, 'heading': 0.0, 'speed': 0.0,
                'battery': 100.0, 'voltage': 24.0, 'signal': 95.0, 'rssi': -60,
                'status': 'IDLE', 'custom_target': None, 'yaw_rate': 0.0,
                'pitch': 0.0, 'roll': 0.0
            }
            self.radar.set_usv_state(usv_id, 0.0, 0.0, 0.0, 'IDLE')
            if hasattr(self, 'ros_node') and self.ros_node:
                self.ros_node.ensure_usv_subscribers(usv_id)
            self.log_event(f"📡 Discovered and registered active external USV: {usv_id}")

    def ingest_external_usv_odom(self, usv_id: str, x: float, y: float, heading: float, speed: float):
        """Called when /usv_{id}/odom is received from an external simulator or hardware."""
        if usv_id not in self.usv_fleet:
            self.register_external_usv(usv_id)
        data = self.usv_fleet[usv_id]
        data['x'] = x
        data['y'] = y
        data['heading'] = heading
        data['speed'] = speed
        data['last_odom_time'] = time.time()

        # Update radar view directly in external mode or when vehicle is selected
        if self.operation_mode == "EXTERNAL" or (self.manual_drive_enabled and usv_id == self.selected_usv):
            self.radar.set_usv_state(usv_id, x, y, heading, data.get('status', 'TRANSIT'))

    def ingest_external_usv_battery(self, usv_id: str, percentage: float, voltage: float):
        """Called when /usv_{id}/battery is received."""
        if usv_id in self.usv_fleet:
            self.usv_fleet[usv_id]['battery'] = percentage
            self.usv_fleet[usv_id]['voltage'] = voltage

    def ingest_external_usv_sonar(self, usv_id: str, range_m: float):
        """Called when /usv_{id}/sensors/sonar is received."""
        if usv_id in self.usv_fleet:
            self.usv_fleet[usv_id]['sonar_range'] = range_m

    def ingest_external_usv_camera(self, usv_id: str, image_bytes: bytes):
        """Called when /usv_{id}/camera/image_raw/compressed is received."""
        if usv_id in self.usv_fleet:
            self.usv_fleet[usv_id]['camera_frame'] = image_bytes
        if hasattr(self, 'video_pip'):
            if getattr(self.video_pip, 'usv_id', None) == usv_id:
                self.video_pip.set_camera_frame(image_bytes)

    # ─── MANUAL DRIVE & SENSOR MODAL ──────────────────────────────────────────

    def _toggle_manual_drive(self, usv_id: Optional[str] = None, force_off: bool = False):
        if force_off or self.manual_drive_enabled:
            old_uid = self.selected_usv
            self.manual_drive_enabled = False
            self.keys_pressed.clear()
            self.manual_banner.setVisible(False)
            self.sidebar.set_manual_drive_active(False)
            self.st_teleop.setText("")
            if old_uid and old_uid in self.usv_fleet:
                self.usv_fleet[old_uid]['status'] = 'HOLD'
                self.usv_fleet[old_uid]['speed'] = 0.0
                self.sidebar.update_inspector(old_uid, self.usv_fleet[old_uid])
                self.usv_cmd_vel_signal.emit(old_uid, 0.0, 0.0)
            self.log_event("Manual teleop drive deactivated.")
        else:
            if not self.selected_usv:
                return
            self.manual_drive_enabled = True
            self.keys_pressed.clear()
            uid = self.selected_usv
            self.usv_fleet[uid]['status'] = 'MANUAL'
            self.sidebar.set_manual_drive_active(True)
            self.manual_banner_label.setText(
                f"🎮 MANUAL DRIVE ACTIVE: {uid}   |   W: Throttle Up  •  S: Reverse/Brake  •  A/D: Steer  •  Space: Stop  •  Esc: Exit"
            )
            self.manual_banner.setVisible(True)
            self.st_teleop.setText(f"🎮 Teleop: {uid}")
            self.log_event(f"Manual teleop drive engaged for {uid}. Steer using W/A/S/D or Arrow keys.")

    def _open_sensor_dialog(self, usv_id: str):
        if not usv_id or usv_id not in self.usv_fleet:
            return
        if self.active_sensor_dialog:
            self.active_sensor_dialog.close()
        self.active_sensor_dialog = SensorDialog(usv_id, self)
        self.active_sensor_dialog.update_telemetry(self.usv_fleet[usv_id])
        self.active_sensor_dialog.show()

    def _open_fleet_analytics_dialog(self):
        if self.active_fleet_dialog:
            self.active_fleet_dialog.close()
        self.active_fleet_dialog = FleetAnalyticsDialog(self)
        self.active_fleet_dialog.update_fleet_telemetry(self.usv_fleet, self.radar.formation_targets)
        self.active_fleet_dialog.show()

    def _open_help_dialog(self, initial_section: str = "getting_started"):
        if not self.active_help_dialog:
            self.active_help_dialog = HelpGuideDialog(self, initial_section=initial_section)
        else:
            self.active_help_dialog._select_section(initial_section)
        self.active_help_dialog.show()
        self.active_help_dialog.raise_()
        self.active_help_dialog.activateWindow()

    def _open_about_dialog(self):
        from PyQt5.QtWidgets import QMessageBox
        about_box = QMessageBox(self)
        about_box.setWindowTitle("About USV Ground Station")
        about_box.setText(
            "<h3>USV Ground Station</h3>"
            "<p><b>Version 2.4.0</b> (ROS 2 Humble / PyQt5)</p>"
            "<p>A tactical Command &amp; Control (C2) and swarm telemetry ground station "
            "for autonomous Unmanned Surface Vehicle fleets.</p>"
            "<p><b>Key Capabilities:</b>"
            "<ul>"
            "<li>Decentralized APF Obstacle Avoidance &amp; Keep-Out Geofencing</li>"
            "<li>WGS84 Georeferencing &amp; Multi-Layer Marine Mapping (ESRI &amp; OpenSeaMap)</li>"
            "<li>Figma-Style Floating Tool Dock with Pan, Waypoints, Boundaries &amp; Ruler</li>"
            "<li>First-Person View Gimbal Camera Feed with Multi-Monitor Pop-Out</li>"
            "<li>Isaac Sim, MATLAB/Simulink &amp; Hardware Bridge Connectors</li>"
            "</ul></p>"
            "<p style='color: #71717a;'>Standardized ROS 2 Humble C2 platform.</p>"
        )
        about_box.setIcon(QMessageBox.Information)
        about_box.exec_()

    # ─── KEYBOARD TELEOP CAPTURE ──────────────────────────────────────────────

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.manual_drive_enabled:
                self._toggle_manual_drive(force_off=True)
            else:
                self._deselect_usv()
            event.accept()
            return

        if self.manual_drive_enabled and not event.isAutoRepeat():
            self.keys_pressed.add(event.key())
            event.accept()
            return

        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if self.manual_drive_enabled and not event.isAutoRepeat():
            self.keys_pressed.discard(event.key())
            event.accept()
            return
        super().keyReleaseEvent(event)

    # ─── MISSION COMMANDS ─────────────────────────────────────────────────────

    def _deploy_formation(self):
        targets = self._calculate_targets()
        for uid in self.usv_fleet:
            self.usv_fleet[uid]['custom_target'] = None
            self.usv_fleet[uid]['status'] = 'FORMATION'
        self.radar.custom_targets.clear()

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
        form_heading_rad = math.radians(self.formation_heading)
        for uid, tpos in targets.items():
            self.usv_target_pose_signal.emit(uid, float(tpos['x']), float(tpos['y']), form_heading_rad)
            self.usv_autonomy_mode_signal.emit(uid, 'FORMATION')
        self.log_event(f"Deployed {self.formation_type} ({len(targets)} USVs)")

    def _hold_position(self):
        for uid in self.usv_fleet:
            self.usv_fleet[uid]['status'] = 'HOLD'
            self.usv_fleet[uid]['speed'] = 0.0
            self.usv_autonomy_mode_signal.emit(uid, 'HOLD')
        self.formation_command_signal.emit({'action': 'HOLD', 'timestamp': time.time()})
        self.log_event("All vehicles commanded to HOLD")

    def _return_home(self):
        self.formation_center = {'x': 0.0, 'y': 0.0}
        self.st_target.setText("Target: (0.0, 0.0)")
        targets = self._calculate_targets()
        form_heading_rad = math.radians(self.formation_heading)
        for uid, tpos in targets.items():
            self.usv_fleet[uid]['custom_target'] = None
            self.usv_fleet[uid]['status'] = 'RTH'
            self.usv_target_pose_signal.emit(uid, float(tpos['x']), float(tpos['y']), form_heading_rad)
            self.usv_autonomy_mode_signal.emit(uid, 'RTH')
        self.radar.custom_targets.clear()
        self.formation_command_signal.emit({
            'action': 'RETURN_HOME',
            'target': {'x': 0, 'y': 0},
            'timestamp': time.time()
        })
        self.log_event("All vehicles commanded to Return to Home (0, 0)")


    def _emergency_stop(self):
        if self.manual_drive_enabled:
            self._toggle_manual_drive(force_off=True)
        for uid in self.usv_fleet:
            self.usv_fleet[uid]['status'] = 'ESTOP'
            self.usv_fleet[uid]['speed'] = 0.0
            self.usv_cmd_vel_signal.emit(uid, 0.0, 0.0)
        self.emergency_stop_signal.emit(True)
        self.log_event("⚠ EMERGENCY STOP ENGAGED")

    # ─── VIEW TOGGLES ─────────────────────────────────────────────────────────

    def _toggle_sidebar(self, visible: bool):
        self.sidebar.setVisible(visible)
        if visible:
            self.splitter.setSizes([max(500, self.width() - 300), 300])
        self.toggle_sidebar_action.blockSignals(True)
        self.toggle_sidebar_action.setChecked(visible)
        self.toggle_sidebar_action.blockSignals(False)
        self.toolbar.set_sidebar_checked(visible)

    def _toggle_console(self, visible: bool):
        self.console_container.setVisible(visible)
        self.toggle_console_action.blockSignals(True)
        self.toggle_console_action.setChecked(visible)
        self.toggle_console_action.blockSignals(False)

    def _toggle_video_feed(self, visible: bool):
        if hasattr(self, 'video_pip'):
            self.video_pip.setVisible(visible)
            if visible:
                if not getattr(self.video_pip, 'is_detached', False):
                    self._reposition_video_pip()
                    self.video_pip.raise_()
                else:
                    self.video_pip.raise_()
                    self.video_pip.activateWindow()
        self.toolbar.set_video_checked(visible)
        self.toggle_video_action.blockSignals(True)
        self.toggle_video_action.setChecked(visible)
        self.toggle_video_action.blockSignals(False)

    def _toggle_video_expanded(self):
        if hasattr(self, 'video_pip'):
            self.video_pip.toggle_expanded()
            self._reposition_video_pip()

    def _toggle_video_detached(self, detach: bool):
        if not hasattr(self, 'video_pip'):
            return
        if detach:
            # Undock to separate OS desktop window (multi-monitor)
            global_pos = self.video_pip.mapToGlobal(QPoint(0, 0))
            self.video_pip.set_detached(True, initial_pos=global_pos)
            self.log_event(f"📺 Detached {self.video_pip.usv_id} video feed to external monitor window")
        else:
            # Dock back into radar canvas
            self.video_pip.set_detached(False, parent=self.radar)
            self._reposition_video_pip()
            self.log_event(f"📺 Docked {self.video_pip.usv_id} video feed back to radar canvas")

    def _reposition_video_pip(self):
        if not hasattr(self, 'video_pip'):
            return
        if getattr(self.video_pip, 'is_detached', False):
            return  # External monitor window: do not override its geometry
        if getattr(self.video_pip, 'is_expanded', False):
            self.video_pip.setGeometry(0, 0, self.radar.width(), self.radar.height())
        else:
            vw, vh = 320, 215
            margin = 12
            if getattr(self.video_pip, 'custom_pos', None) is not None:
                cx, cy = self.video_pip.custom_pos
                # Keep within bounds of radar canvas
                x = max(0, min(cx, max(0, self.radar.width() - vw)))
                y = max(0, min(cy, max(0, self.radar.height() - vh)))
                self.video_pip.custom_pos = (x, y)
            else:
                x = max(10, self.radar.width() - vw - margin)
                y = 12
            self.video_pip.setGeometry(x, y, vw, vh)
        self.video_pip.raise_()
        if hasattr(self.radar, 'toolbar') and self.radar.toolbar:
            self.radar.toolbar.raise_()



    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_video_pip()

    # ─── SIMULATION TICK ──────────────────────────────────────────────────────

    def _tick(self):
        elapsed = int(time.time() - self.start_time)
        mins, secs = divmod(elapsed, 60)
        self.st_uptime.setText(f"{mins:02d}:{secs:02d}")

        self.radar.update_animation()

        # Natural Metocean subtle drift (Regional Forecast Report)
        if random.random() < 0.04:
            self.weather_report['wind_spd'] = max(4.0, min(25.0, self.weather_report['wind_spd'] + random.uniform(-0.15, 0.15)))
            self.weather_report['current_spd'] = max(0.1, min(3.0, self.weather_report['current_spd'] + random.uniform(-0.04, 0.04)))
            self.weather_report['depth'] = max(5.0, min(50.0, self.weather_report['depth'] + random.uniform(-0.02, 0.02)))

        t_now = time.time()
        for idx, (uid, data) in enumerate(self.usv_fleet.items()):
            # Hydrodynamic wave pitch/roll
            data['pitch'] = math.sin(t_now * 2.2 + idx * 1.4) * (1.2 + data['speed'] * 0.4)
            data['roll'] = math.cos(t_now * 1.8 + idx * 1.1) * (0.8 + data['speed'] * 0.3)
            # Drone in-situ micro-climate anemometer & doppler variance
            if 'met_data' in data and random.random() < 0.05:
                m = data['met_data']
                m['wind_spd'] = max(2.0, min(35.0, m['wind_spd'] + random.uniform(-0.12, 0.12)))
                m['wind_gust'] = max(m['wind_spd'], m['wind_spd'] * 1.25 + random.uniform(0, 0.8))
                m['current_spd'] = max(0.1, min(4.0, m['current_spd'] + random.uniform(-0.03, 0.03)))

        # Update Metocean Data across sidebar and radar
        drone_mets = {uid: d.get('met_data', {}) for uid, d in self.usv_fleet.items()}
        self.sidebar.update_metocean_data(self.weather_report, drone_mets)

        active_uid = self.selected_usv or 'USV-1'
        active_drone_met = self.usv_fleet[active_uid].get('met_data') if active_uid in self.usv_fleet else None
        self.radar.set_metocean_data(self.weather_report, active_drone_met)

        if self.simulation_enabled:
            dt = 0.033

            # ── 1. Manual Keyboard Drive Simulation & Teleop ──
            if self.manual_drive_enabled and self.selected_usv in self.usv_fleet:
                data = self.usv_fleet[self.selected_usv]
                throttle, turn = 0.0, 0.0

                if Qt.Key_W in self.keys_pressed or Qt.Key_Up in self.keys_pressed:
                    throttle += 1.0
                if Qt.Key_S in self.keys_pressed or Qt.Key_Down in self.keys_pressed:
                    throttle -= 0.6
                if Qt.Key_A in self.keys_pressed or Qt.Key_Left in self.keys_pressed:
                    turn += 2.2
                if Qt.Key_D in self.keys_pressed or Qt.Key_Right in self.keys_pressed:
                    turn -= 2.2
                if Qt.Key_Space in self.keys_pressed:
                    throttle = 0.0
                    data['speed'] *= 0.85

                data['yaw_rate'] = turn

                # Emit cmd_vel for external simulator / hardware teleoperation
                cmd_linear_x = throttle * 2.5 if throttle != 0.0 else (data['speed'] if abs(data['speed']) > 0.05 else 0.0)
                cmd_angular_z = turn
                self.usv_cmd_vel_signal.emit(self.selected_usv, float(cmd_linear_x), float(cmd_angular_z))

                if self.operation_mode == "SIMULATION":
                    data['heading'] = (data['heading'] + turn * dt) % (2.0 * math.pi)

                    if throttle != 0.0:
                        data['speed'] = max(-1.2, min(5.5, data['speed'] + throttle * 3.5 * dt))
                    else:
                        data['speed'] *= 0.96  # hydrodynamic drag

                    data['x'] += math.cos(data['heading']) * data['speed'] * dt
                    data['y'] += math.sin(data['heading']) * data['speed'] * dt
                    data['battery'] = max(0.0, data['battery'] - (0.002 if abs(data['speed']) > 0.1 else 0.0005))

            # ── 2. Autonomous Navigation Simulation (Only in SIMULATION Mode) ──
            if self.operation_mode == "SIMULATION":
                targets = self.radar.formation_targets
                max_spd, max_turn = 3.5, 1.8

                for uid, data in self.usv_fleet.items():
                    if self.manual_drive_enabled and uid == self.selected_usv:
                        self.radar.set_usv_state(uid, data['x'], data['y'], data['heading'], 'MANUAL')
                        continue

                    # Destination target (custom waypoint takes priority over swarm target)
                    dest = data.get('custom_target') or (targets.get(uid) if data['status'] in ('FORMATION', 'RTH', 'AVOIDING') else None)

                    if dest:
                        tx, ty = dest['x'], dest['y']
                        dx, dy = tx - data['x'], ty - data['y']
                        dist = math.hypot(dx, dy)

                        # ── Autonomous Obstacle Avoidance (APF) ──
                        repel_x, repel_y = 0.0, 0.0
                        is_avoiding = False
                        for obs in self.radar.detected_obstacles:
                            ox, oy = obs['x'], obs['y']
                            obs_d = math.hypot(data['x'] - ox, data['y'] - oy)
                            safe_r = obs.get('radius', 5.0) + 4.0
                            if obs_d < safe_r:
                                is_avoiding = True
                                force = (safe_r - obs_d) * 4.0
                                bearing_away = math.atan2(data['y'] - oy, data['x'] - ox)
                                repel_x += math.cos(bearing_away) * force
                                repel_y += math.sin(bearing_away) * force

                        # ── Keep-Out Boundary Avoidance (Geofences) ──
                        for gf in getattr(self.radar, 'geofences', []):
                            pts = gf.get('points', [])
                            if len(pts) >= 3:
                                if point_in_polygon(data['x'], data['y'], pts):
                                    is_avoiding = True
                                    # Drone breached keep-out zone: find nearest boundary edge and push strongly outward
                                    best_d = 999999.0
                                    best_qx, best_qy = pts[0]
                                    for i in range(len(pts)):
                                        p1, p2 = pts[i], pts[(i + 1) % len(pts)]
                                        seg_d, qx, qy = dist_to_segment(data['x'], data['y'], p1[0], p1[1], p2[0], p2[1])
                                        if seg_d < best_d:
                                            best_d = seg_d
                                            best_qx, best_qy = qx, qy
                                    bearing_out = math.atan2(data['y'] - best_qy, data['x'] - best_qx)
                                    repel_x += math.cos(bearing_out) * 12.0
                                    repel_y += math.sin(bearing_out) * 12.0
                                else:
                                    for i in range(len(pts)):
                                        p1, p2 = pts[i], pts[(i + 1) % len(pts)]
                                        seg_d, qx, qy = dist_to_segment(data['x'], data['y'], p1[0], p1[1], p2[0], p2[1])
                                        if seg_d < 6.0:
                                            is_avoiding = True
                                            force = (6.0 - seg_d) * 5.0
                                            bearing_away = math.atan2(data['y'] - qy, data['x'] - qx)
                                            repel_x += math.cos(bearing_away) * force
                                            repel_y += math.sin(bearing_away) * force

                        if is_avoiding:
                            data['status'] = 'AVOIDING'
                            dx += repel_x
                            dy += repel_y
                            dist = math.hypot(dx, dy)
                        elif data['status'] == 'AVOIDING':
                            data['status'] = 'FORMATION' if not data.get('custom_target') else 'TRANSIT'

                        if dist > 0.35:
                            desired = math.atan2(dy, dx)
                            diff = (desired - data['heading'] + math.pi) % (2.0 * math.pi) - math.pi
                            turn = max(-max_turn * dt, min(max_turn * dt, diff * 2.2))
                            data['heading'] += turn
                            data['yaw_rate'] = turn / dt
                            data['speed'] = min(max_spd, max(0.4, dist * 0.8))
                            data['x'] += math.cos(data['heading']) * data['speed'] * dt
                            data['y'] += math.sin(data['heading']) * data['speed'] * dt
                        else:
                            data['speed'] = 0.0
                            data['yaw_rate'] = 0.0
                            if data.get('custom_target'):
                                data['status'] = 'HOLD'

                        data['battery'] = max(0.0, data['battery'] - 0.001)

                    # RF link signal fluctuation
                    if random.random() < 0.05:
                        jitter = random.choice([-1.0, 0.0, 1.0])
                        data['signal'] = max(80.0, min(100.0, data['signal'] + jitter * 0.5))
                        data['rssi'] = int(-68 + (data['signal'] - 80) * 0.7)

                    self.radar.set_usv_state(uid, data['x'], data['y'], data['heading'], data['status'])
            else:
                # In EXTERNAL mode, update radar markers with latest received external poses
                for uid, data in self.usv_fleet.items():
                    status = 'MANUAL' if (self.manual_drive_enabled and uid == self.selected_usv) else data.get('status', 'ONLINE')
                    self.radar.set_usv_state(uid, data['x'], data['y'], data['heading'], status)

        # ── 4. ROS 2 Downlink Telemetry Broadcast (Target Pose & Autonomy Mode) ──
        # Runs at 5 Hz regardless of simulation physics pause, so external craft receive orders
        if not hasattr(self, '_downlink_tick_counter'):
            self._downlink_tick_counter = 0
        self._downlink_tick_counter += 1

        if self._downlink_tick_counter % 6 == 0:  # 5 Hz at 30 Hz tick
            form_heading_rad = math.radians(self.formation_heading)
            targets = self.radar.formation_targets
            for uid, data in self.usv_fleet.items():
                mode = 'MANUAL' if (self.manual_drive_enabled and uid == self.selected_usv) else data.get('status', 'IDLE')
                self.usv_autonomy_mode_signal.emit(uid, mode)
                dest = data.get('custom_target') or targets.get(uid)
                if dest:
                    self.usv_target_pose_signal.emit(uid, float(dest['x']), float(dest['y']), form_heading_rad)

        # Update sidebar

        self.sidebar.update_fleet_rows(self.usv_fleet)
        if self.selected_usv and self.selected_usv in self.usv_fleet:
            self.sidebar.update_inspector(self.selected_usv, self.usv_fleet[self.selected_usv])
        elif self.selected_usv is None:
            self.sidebar.show_fleet_overview(self.usv_fleet, self.formation_type, self.formation_center)

        # Update video feed PiP and status bar network metrics
        active_drone = self.usv_fleet.get(active_uid, {})
        if hasattr(self, 'video_pip') and self.video_pip.isVisible():
            self.video_pip.update_telemetry(active_drone)
            if hasattr(self, 'st_network'):
                self.st_network.setText(
                    f"📶 {active_drone.get('rssi', -62)} dBm · ↓ {self.video_pip.downlink_mbps:.1f}M ↑ {self.video_pip.uplink_mbps:.1f}M · {self.video_pip.latency_ms}ms"
                )

        # Update live sensor dialog if open
        if self.active_sensor_dialog and self.active_sensor_dialog.isVisible():
            if self.active_sensor_dialog.usv_id in self.usv_fleet:
                self.active_sensor_dialog.update_telemetry(self.usv_fleet[self.active_sensor_dialog.usv_id], self.weather_report)

        # Update live fleet analytics dialog if open
        if self.active_fleet_dialog and self.active_fleet_dialog.isVisible():
            self.active_fleet_dialog.update_fleet_telemetry(self.usv_fleet, self.radar.formation_targets)

    # ─── LOGGING ──────────────────────────────────────────────────────────────

    def log_event(self, message: str):
        ts = time.strftime("%H:%M:%S")
        self.log_console.append(f"<span style='color:#3f3f46;'>[{ts}]</span> {message}")
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())

    def closeEvent(self, event):
        if hasattr(self, 'anim_timer') and self.anim_timer.isActive():
            self.anim_timer.stop()
        super().closeEvent(event)

