"""
HERMORD Ground Station Main Window.
Simplified, clean interface adhering to Shadcn UI design:
- Menus for secondary controls (Swarm size, physics toggle, view options)
- Expansive Tactical Map as primary hero canvas
- Tabbed contextual sidebar (Formation Control vs Fleet Telemetry)
- Collapsible bottom activity console
"""

import sys
import math
import time
import json
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QKeySequence
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QSlider, QTableWidget,
    QTableWidgetItem, QHeaderView, QTextEdit, QGroupBox,
    QFrame, QSplitter, QTabWidget, QAction, QActionGroup
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

/* Menu Bar */
QMenuBar {
    background-color: #09090b;
    color: #a1a1aa;
    border-bottom: 1px solid #1c1c1f;
    padding: 2px 6px;
    font-size: 12px;
}
QMenuBar::item {
    background: transparent;
    padding: 4px 8px;
    border-radius: 4px;
}
QMenuBar::item:selected {
    background: #18181b;
    color: #fafafa;
}
QMenu {
    background-color: #121215;
    border: 1px solid #27272a;
    border-radius: 6px;
    padding: 4px;
    color: #fafafa;
    font-size: 12px;
}
QMenu::item {
    padding: 6px 20px 6px 12px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #27272a;
    color: #fafafa;
}
QMenu::separator {
    height: 1px;
    background: #27272a;
    margin: 4px 0;
}

/* Tabs (Shadcn Segmented Switch) */
QTabWidget::pane {
    border: 1px solid #27272a;
    border-radius: 8px;
    background-color: #121215;
    top: -1px;
}
QTabBar::tab {
    background: #0c0c0e;
    color: #a1a1aa;
    border: 1px solid #27272a;
    padding: 8px 16px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-size: 12px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background: #18181b;
    color: #fafafa;
    border-bottom: 1px solid #18181b;
    font-weight: 600;
}
QTabBar::tab:hover:!selected {
    background: #141418;
    color: #d4d4d8;
}

/* Card / Group Containers */
QGroupBox {
    border: 1px solid #27272a;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 12px;
    background-color: #121215;
    font-size: 12px;
    font-weight: 600;
    color: #a1a1aa;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    left: 10px;
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

/* Shadcn Primary Button */
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

/* Log Console */
QTextEdit {
    background-color: #09090b;
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
        self.resize(1180, 760)
        self.setStyleSheet(SHADCN_STYLESHEET)

        # Swarm State
        self.formation_center = {'x': 0.0, 'y': 0.0}
        self.formation_type = "V-Shape"
        self.formation_spacing = 15.0  # meters
        self.formation_heading = 90.0  # degrees
        self.simulation_enabled = True
        self.selected_usv = "USV-1"

        # Initialize USVs
        self.usv_fleet = {
            'USV-1': {'x': -15.0, 'y': -15.0, 'heading': 0.0, 'speed': 0.0, 'battery': 94.0, 'status': 'IDLE'},
            'USV-2': {'x': -10.0, 'y': -25.0, 'heading': 0.0, 'speed': 0.0, 'battery': 88.0, 'status': 'IDLE'},
            'USV-3': {'x': 10.0,  'y': -25.0, 'heading': 0.0, 'speed': 0.0, 'battery': 91.0, 'status': 'IDLE'},
            'USV-4': {'x': 15.0,  'y': -15.0, 'heading': 0.0, 'speed': 0.0, 'battery': 85.0, 'status': 'IDLE'},
        }

        self.start_time = time.time()
        self._init_menu_bar()
        self._init_ui()
        self._calculate_formation_targets()
        self._select_usv("USV-1")

        # Animation & Physics Timer (30 Hz)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._tick)
        self.anim_timer.start(33)

        self.log_event("Ground Station initialized. Ready for swarm deployment.")

    def _init_menu_bar(self):
        menubar = self.menuBar()

        # 1. Mission Menu
        mission_menu = menubar.addMenu("Mission")

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

        reset_coord_act = QAction("Reset Target to (0, 0)", self)
        reset_coord_act.triggered.connect(lambda: self._on_waypoint_selected(0.0, 0.0))
        mission_menu.addAction(reset_coord_act)

        # 2. Fleet Menu
        fleet_menu = menubar.addMenu("Fleet")

        size_menu = fleet_menu.addMenu("Swarm Size")
        size_group = QActionGroup(self)
        for count in [2, 3, 4, 5, 6]:
            act = QAction(f"{count} USVs", self, checkable=True)
            if count == 4:
                act.setChecked(True)
            act.triggered.connect(lambda checked, c=count: self._on_fleet_count_changed(f"{c} USVs"))
            size_group.addAction(act)
            size_menu.addAction(act)

        fleet_menu.addSeparator()

        self.sim_action = QAction("Enable Kinematics Simulation", self, checkable=True)
        self.sim_action.setChecked(True)
        self.sim_action.toggled.connect(lambda val: setattr(self, 'simulation_enabled', val))
        fleet_menu.addAction(self.sim_action)

        # 3. View Menu
        view_menu = menubar.addMenu("View")

        center_map_act = QAction("Center View on Origin", self)
        center_map_act.setShortcut(QKeySequence("Ctrl+0"))
        center_map_act.triggered.connect(lambda: self.radar.reset_view())
        view_menu.addAction(center_map_act)

        zoom_in_act = QAction("Zoom In", self)
        zoom_in_act.setShortcut(QKeySequence("Ctrl+="))
        zoom_in_act.triggered.connect(lambda: setattr(self.radar, 'scale', min(50.0, self.radar.scale * 1.25)))
        view_menu.addAction(zoom_in_act)

        zoom_out_act = QAction("Zoom Out", self)
        zoom_out_act.setShortcut(QKeySequence("Ctrl+-"))
        zoom_out_act.triggered.connect(lambda: setattr(self.radar, 'scale', max(2.0, self.radar.scale * 0.8)))
        view_menu.addAction(zoom_out_act)

        view_menu.addSeparator()

        self.toggle_log_action = QAction("Show Activity Console", self, checkable=True)
        self.toggle_log_action.setChecked(False)
        self.toggle_log_action.toggled.connect(self._toggle_console_visibility)
        view_menu.addAction(self.toggle_log_action)

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(8)

        # 1. Top Header Bar
        main_layout.addWidget(self._create_header_bar())

        # 2. Main Content: Map Canvas (Hero, 68%) | Contextual Sidebar (32%)
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._create_map_panel())
        splitter.addWidget(self._create_sidebar())
        splitter.setStretchFactor(0, 7)
        splitter.setStretchFactor(1, 3)
        main_layout.addWidget(splitter, stretch=1)

        # 3. Collapsible Console (Hidden by default to keep screen clean)
        self.log_container = self._create_log_panel()
        self.log_container.setVisible(False)
        main_layout.addWidget(self.log_container)

    def _create_header_bar(self):
        bar = QFrame()
        bar.setStyleSheet("background-color: #121215; border-radius: 8px; border: 1px solid #27272a; padding: 4px;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 6, 14, 6)

        # Title
        title_box = QHBoxLayout()
        title_label = QLabel("Ground Station")
        title_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #fafafa;")
        title_box.addWidget(title_label)

        sub_label = QLabel("// USV Swarm Controller")
        sub_label.setStyleSheet("font-size: 12px; color: #71717a;")
        title_box.addWidget(sub_label)
        layout.addLayout(title_box)

        layout.addStretch()

        # Status Pills
        self.ros_badge = QLabel("● ROS 2 Connected")
        self.ros_badge.setStyleSheet("color: #34d399; font-weight: 500; font-size: 11px; padding: 3px 10px; background: #064e3b; border-radius: 9999px; border: 1px solid #047857;")
        layout.addWidget(self.ros_badge)

        self.fleet_badge = QLabel("4 USVs")
        self.fleet_badge.setStyleSheet("color: #e4e4e7; font-weight: 500; font-size: 11px; padding: 3px 10px; background: #18181b; border-radius: 9999px; border: 1px solid #27272a;")
        layout.addWidget(self.fleet_badge)

        self.uptime_label = QLabel("00:00")
        self.uptime_label.setStyleSheet("color: #71717a; font-size: 11px; font-family: Menlo, monospace;")
        layout.addWidget(self.uptime_label)

        # Toggle Console Button
        self.console_btn = QPushButton("Console")
        self.console_btn.setFixedHeight(26)
        self.console_btn.setStyleSheet("font-size: 11px; padding: 2px 8px; background: #18181b; border: 1px solid #27272a;")
        self.console_btn.clicked.connect(self._toggle_console)
        layout.addWidget(self.console_btn)

        return bar

    def _create_map_panel(self):
        panel = QFrame()
        panel.setStyleSheet("background-color: #0c0c0e; border: 1px solid #27272a; border-radius: 8px;")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tactical Canvas
        self.radar = RadarWidget()
        self.radar.waypoint_selected.connect(self._on_waypoint_selected)
        self.radar.usv_selected.connect(self._select_usv)
        layout.addWidget(self.radar, stretch=1)

        # Floating Bottom Bar on Map
        hud_bar = QFrame()
        hud_bar.setStyleSheet("background-color: #121215; border-top: 1px solid #27272a; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px; padding: 4px;")
        h_layout = QHBoxLayout(hud_bar)
        h_layout.setContentsMargins(10, 4, 10, 4)

        self.waypoint_lbl = QLabel("Target: (0.0, 0.0)m")
        self.waypoint_lbl.setStyleSheet("color: #38bdf8; font-family: Menlo, monospace; font-size: 11px;")
        h_layout.addWidget(self.waypoint_lbl)

        h_layout.addStretch()

        reset_btn = QPushButton("Center Origin")
        reset_btn.setFixedHeight(24)
        reset_btn.setStyleSheet("font-size: 10px; padding: 2px 8px;")
        reset_btn.clicked.connect(self.radar.reset_view)
        h_layout.addWidget(reset_btn)

        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedSize(24, 24)
        zoom_in_btn.setStyleSheet("font-size: 12px; font-weight: bold; padding: 0;")
        zoom_in_btn.clicked.connect(lambda: setattr(self.radar, 'scale', min(50.0, self.radar.scale * 1.25)))
        h_layout.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("-")
        zoom_out_btn.setFixedSize(24, 24)
        zoom_out_btn.setStyleSheet("font-size: 12px; font-weight: bold; padding: 0;")
        zoom_out_btn.clicked.connect(lambda: setattr(self.radar, 'scale', max(2.0, self.radar.scale * 0.8)))
        h_layout.addWidget(zoom_out_btn)

        layout.addWidget(hud_bar)
        return panel

    def _create_sidebar(self):
        tabs = QTabWidget()
        tabs.addTab(self._create_formation_tab(), "Formation")
        tabs.addTab(self._create_fleet_tab(), "Fleet Telemetry")
        return tabs

    def _create_formation_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(12)

        # Formation Selection
        layout.addWidget(QLabel("Formation Pattern:"))
        self.form_combo = QComboBox()
        self.form_combo.addItems(["V-Shape", "Line (Abeam)", "Column (In-line)", "Circle", "Diamond"])
        self.form_combo.currentTextChanged.connect(self._on_formation_type_changed)
        layout.addWidget(self.form_combo)

        # Spacing Slider
        spacing_header = QHBoxLayout()
        spacing_title = QLabel("Vehicle Spacing")
        spacing_title.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        spacing_header.addWidget(spacing_title)
        spacing_header.addStretch()
        self.spacing_val_lbl = QLabel(f"{int(self.formation_spacing)} m")
        self.spacing_val_lbl.setStyleSheet("color: #fafafa; font-weight: 600; font-size: 11px; background: #0c0c0e; padding: 2px 6px; border-radius: 4px; border: 1px solid #27272a;")
        spacing_header.addWidget(self.spacing_val_lbl)
        layout.addLayout(spacing_header)

        self.spacing_slider = QSlider(Qt.Horizontal)
        self.spacing_slider.setRange(5, 50)
        self.spacing_slider.setValue(int(self.formation_spacing))
        self.spacing_slider.valueChanged.connect(self._on_spacing_changed)
        layout.addWidget(self.spacing_slider)

        # Bearing Slider
        bearing_header = QHBoxLayout()
        bearing_title = QLabel("Formation Bearing")
        bearing_title.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        bearing_header.addWidget(bearing_title)
        bearing_header.addStretch()
        self.heading_val_lbl = QLabel(f"{int(self.formation_heading)}°")
        self.heading_val_lbl.setStyleSheet("color: #fafafa; font-weight: 600; font-size: 11px; background: #0c0c0e; padding: 2px 6px; border-radius: 4px; border: 1px solid #27272a;")
        bearing_header.addWidget(self.heading_val_lbl)
        layout.addLayout(bearing_header)

        self.heading_slider = QSlider(Qt.Horizontal)
        self.heading_slider.setRange(0, 359)
        self.heading_slider.setValue(int(self.formation_heading))
        self.heading_slider.valueChanged.connect(self._on_heading_changed)
        layout.addWidget(self.heading_slider)

        layout.addSpacing(8)

        # Action Buttons
        self.deploy_btn = QPushButton("Deploy Formation")
        self.deploy_btn.setObjectName("primaryBtn")
        self.deploy_btn.setFixedHeight(36)
        self.deploy_btn.clicked.connect(self._deploy_formation)
        layout.addWidget(self.deploy_btn)

        row_layout = QHBoxLayout()
        self.hold_btn = QPushButton("Hold")
        self.hold_btn.setFixedHeight(32)
        self.hold_btn.clicked.connect(self._hold_position)
        row_layout.addWidget(self.hold_btn)

        self.rth_btn = QPushButton("Return Home")
        self.rth_btn.setFixedHeight(32)
        self.rth_btn.clicked.connect(self._return_home)
        row_layout.addWidget(self.rth_btn)
        layout.addLayout(row_layout)

        layout.addSpacing(10)

        # Emergency Stop
        self.estop_btn = QPushButton("Emergency Stop")
        self.estop_btn.setObjectName("destructiveBtn")
        self.estop_btn.setFixedHeight(38)
        self.estop_btn.clicked.connect(self._emergency_stop)
        layout.addWidget(self.estop_btn)

        layout.addStretch()
        return tab

    def _create_fleet_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(8)

        # Table of USVs
        self.fleet_table = QTableWidget(len(self.usv_fleet), 5)
        self.fleet_table.setHorizontalHeaderLabels(["ID", "Pos", "Speed", "Bat", "Status"])
        self.fleet_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.fleet_table.verticalHeader().setVisible(False)
        self.fleet_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.fleet_table.setSelectionMode(QTableWidget.SingleSelection)
        self.fleet_table.itemSelectionChanged.connect(self._on_table_selection_changed)

        for row, (usv_id, data) in enumerate(self.usv_fleet.items()):
            self.fleet_table.setItem(row, 0, QTableWidgetItem(usv_id))
            self.fleet_table.setItem(row, 1, QTableWidgetItem(f"{data['x']:.0f},{data['y']:.0f}"))
            self.fleet_table.setItem(row, 2, QTableWidgetItem(f"{data['speed']:.1f}"))
            self.fleet_table.setItem(row, 3, QTableWidgetItem(f"{int(data['battery'])}%"))
            self.fleet_table.setItem(row, 4, QTableWidgetItem(data['status']))

        layout.addWidget(self.fleet_table, stretch=2)

        # Selected USV Inspector Card
        self.inspector_card = QFrame()
        self.inspector_card.setStyleSheet("background-color: #0c0c0e; border: 1px solid #27272a; border-radius: 6px; padding: 8px;")
        ins_layout = QVBoxLayout(self.inspector_card)
        ins_layout.setContentsMargins(8, 6, 8, 6)
        ins_layout.setSpacing(5)

        ins_header = QHBoxLayout()
        self.ins_title = QLabel("USV-1 Details")
        self.ins_title.setStyleSheet("font-weight: 600; font-size: 12px; color: #38bdf8;")
        ins_header.addWidget(self.ins_title)
        ins_header.addStretch()

        self.ins_status_pill = QLabel("● IDLE")
        self.ins_status_pill.setStyleSheet("font-size: 10px; font-weight: 600; padding: 2px 6px; background: #18181b; border: 1px solid #27272a; border-radius: 4px; color: #a1a1aa;")
        ins_header.addWidget(self.ins_status_pill)
        ins_layout.addLayout(ins_header)

        # Metrics Grid
        t_grid = QGridLayout()
        t_grid.setHorizontalSpacing(8)
        t_grid.setVerticalSpacing(3)

        t_grid.addWidget(QLabel("Position:"), 0, 0)
        self.ins_pos = QLabel("X: -15.0m, Y: -15.0m")
        self.ins_pos.setStyleSheet("color: #fafafa; font-family: Menlo, monospace; font-size: 11px;")
        t_grid.addWidget(self.ins_pos, 0, 1)

        t_grid.addWidget(QLabel("Heading:"), 1, 0)
        self.ins_hdg = QLabel("0° (East)")
        self.ins_hdg.setStyleSheet("color: #fafafa; font-size: 11px;")
        t_grid.addWidget(self.ins_hdg, 1, 1)

        t_grid.addWidget(QLabel("Velocity:"), 2, 0)
        self.ins_spd = QLabel("0.0 m/s (0.0 kts)")
        self.ins_spd.setStyleSheet("color: #fafafa; font-size: 11px;")
        t_grid.addWidget(self.ins_spd, 2, 1)

        t_grid.addWidget(QLabel("Target Dist:"), 3, 0)
        self.ins_slot_dist = QLabel("0.0 m")
        self.ins_slot_dist.setStyleSheet("color: #38bdf8; font-family: Menlo, monospace; font-size: 11px;")
        t_grid.addWidget(self.ins_slot_dist, 3, 1)

        t_grid.addWidget(QLabel("Battery:"), 4, 0)
        self.ins_bat = QLabel("94% · 24.8V")
        self.ins_bat.setStyleSheet("color: #34d399; font-weight: 500; font-size: 11px;")
        t_grid.addWidget(self.ins_bat, 4, 1)

        ins_layout.addLayout(t_grid)

        # Inspector Actions Bar
        ins_btn_layout = QHBoxLayout()
        self.focus_btn = QPushButton("Focus on Map")
        self.focus_btn.setFixedHeight(26)
        self.focus_btn.setStyleSheet("font-size: 11px; padding: 2px 6px;")
        self.focus_btn.clicked.connect(self._focus_selected_usv)
        ins_btn_layout.addWidget(self.focus_btn)

        self.solo_hold_btn = QPushButton("Hold Vehicle")
        self.solo_hold_btn.setFixedHeight(26)
        self.solo_hold_btn.setStyleSheet("font-size: 11px; padding: 2px 6px;")
        self.solo_hold_btn.clicked.connect(self._hold_selected_usv)
        ins_btn_layout.addWidget(self.solo_hold_btn)

        ins_layout.addLayout(ins_btn_layout)
        layout.addWidget(self.inspector_card, stretch=3)

        # Fleet Average Footer
        footer = QHBoxLayout()
        footer.addWidget(QLabel("Avg Battery:"))
        self.avg_bat_lbl = QLabel("89%")
        self.avg_bat_lbl.setStyleSheet("color: #34d399; font-weight: 600; font-size: 11px;")
        footer.addWidget(self.avg_bat_lbl)
        footer.addStretch()
        footer.addWidget(QLabel("Centroid:"))
        self.swarm_center_lbl = QLabel("(0m, 0m)")
        self.swarm_center_lbl.setStyleSheet("color: #a1a1aa; font-family: Menlo, monospace; font-size: 11px;")
        footer.addWidget(self.swarm_center_lbl)
        layout.addLayout(footer)

        return tab

    def _create_log_panel(self):
        group = QGroupBox("Activity Console")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumHeight(90)
        layout.addWidget(self.log_console)

        return group

    def _toggle_console(self):
        visible = not self.log_container.isVisible()
        self._toggle_console_visibility(visible)

    def _toggle_console_visibility(self, visible):
        self.log_container.setVisible(visible)
        self.toggle_log_action.setChecked(visible)
        self.console_btn.setStyleSheet(
            "font-size: 11px; padding: 2px 8px; background: #27272a; border: 1px solid #38bdf8;"
            if visible else
            "font-size: 11px; padding: 2px 8px; background: #18181b; border: 1px solid #27272a;"
        )

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
        self.log_event(f"Formation pattern: {text}")

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
        self.fleet_badge.setText(f"{count} USVs")
        self._update_fleet_table_structure()
        self._calculate_formation_targets()
        if self.selected_usv not in self.usv_fleet:
            self._select_usv("USV-1")
        self.log_event(f"Swarm size updated to {count} vehicles.")

    def _update_fleet_table_structure(self):
        self.fleet_table.blockSignals(True)
        self.fleet_table.setRowCount(len(self.usv_fleet))
        for row, (usv_id, data) in enumerate(self.usv_fleet.items()):
            self.fleet_table.setItem(row, 0, QTableWidgetItem(usv_id))
            self.fleet_table.setItem(row, 1, QTableWidgetItem(f"{data['x']:.0f},{data['y']:.0f}"))
            self.fleet_table.setItem(row, 2, QTableWidgetItem(f"{data['speed']:.1f}"))
            self.fleet_table.setItem(row, 3, QTableWidgetItem(f"{int(data['battery'])}%"))
            self.fleet_table.setItem(row, 4, QTableWidgetItem(data['status']))
        self.fleet_table.blockSignals(False)

    def _select_usv(self, usv_id):
        if usv_id not in self.usv_fleet:
            return
        self.selected_usv = usv_id
        self.radar.selected_usv = usv_id
        self.radar.update()

        self.fleet_table.blockSignals(True)
        for row in range(self.fleet_table.rowCount()):
            item = self.fleet_table.item(row, 0)
            if item and item.text() == usv_id:
                self.fleet_table.selectRow(row)
                break
        self.fleet_table.blockSignals(False)

        self._update_inspector()

    def _on_table_selection_changed(self):
        selected_rows = self.fleet_table.selectedIndexes()
        if selected_rows:
            row = selected_rows[0].row()
            usv_id_item = self.fleet_table.item(row, 0)
            if usv_id_item:
                usv_id = usv_id_item.text()
                self._select_usv(usv_id)

    def _focus_selected_usv(self):
        if hasattr(self, 'selected_usv') and self.selected_usv in self.usv_fleet:
            self.radar.focus_usv(self.selected_usv)
            self.log_event(f"Map centered on {self.selected_usv}")

    def _hold_selected_usv(self):
        if hasattr(self, 'selected_usv') and self.selected_usv in self.usv_fleet:
            self.usv_fleet[self.selected_usv]['status'] = 'HOLD'
            self.usv_fleet[self.selected_usv]['speed'] = 0.0
            self.log_event(f"Commanded solo HOLD for {self.selected_usv}")
            self._update_inspector()

    def _update_inspector(self):
        if not hasattr(self, 'selected_usv') or self.selected_usv not in self.usv_fleet:
            return

        usv_id = self.selected_usv
        data = self.usv_fleet[usv_id]

        self.ins_title.setText(f"{usv_id} Details")
        self.ins_status_pill.setText(f"● {data['status']}")

        st = data['status']
        if st == 'FORMATION':
            self.ins_status_pill.setStyleSheet("font-size: 10px; font-weight: 600; padding: 2px 6px; background: #0c4a6e; border: 1px solid #0284c7; border-radius: 4px; color: #38bdf8;")
        elif st == 'RTH':
            self.ins_status_pill.setStyleSheet("font-size: 10px; font-weight: 600; padding: 2px 6px; background: #064e3b; border: 1px solid #059669; border-radius: 4px; color: #34d399;")
        elif st == 'ESTOP':
            self.ins_status_pill.setStyleSheet("font-size: 10px; font-weight: 600; padding: 2px 6px; background: #450a0a; border: 1px solid #dc2626; border-radius: 4px; color: #f87171;")
        else:
            self.ins_status_pill.setStyleSheet("font-size: 10px; font-weight: 600; padding: 2px 6px; background: #18181b; border: 1px solid #27272a; border-radius: 4px; color: #a1a1aa;")

        self.ins_pos.setText(f"X: {data['x']:+.1f}m, Y: {data['y']:+.1f}m")

        hdg_deg = int(math.degrees(data['heading']) % 360)
        dirs = ["E", "NE", "N", "NW", "W", "SW", "S", "SE", "E"]
        dir_idx = int((hdg_deg + 22.5) // 45) % 8
        self.ins_hdg.setText(f"{hdg_deg}° ({dirs[dir_idx]})")

        knots = data['speed'] * 1.94384
        self.ins_spd.setText(f"{data['speed']:.1f} m/s ({knots:.1f} kts)")

        if usv_id in self.radar.formation_targets:
            tp = self.radar.formation_targets[usv_id]
            d = math.hypot(tp['x'] - data['x'], tp['y'] - data['y'])
            self.ins_slot_dist.setText(f"{d:.1f} m")
        else:
            self.ins_slot_dist.setText("None")

        est_voltage = 22.0 + (data['battery'] / 100.0) * 3.2
        self.ins_bat.setText(f"{int(data['battery'])}% · {est_voltage:.1f}V")

    def _on_waypoint_selected(self, wx, wy):
        self.formation_center = {'x': wx, 'y': wy}
        self.waypoint_lbl.setText(f"Target: ({wx:.1f}, {wy:.1f})m")
        self._calculate_formation_targets()
        self.log_event(f"Target location: ({wx:.1f}m, {wy:.1f}m)")

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
                self.fleet_table.item(row, 1).setText(f"{data['x']:.0f},{data['y']:.0f}")
                self.fleet_table.item(row, 2).setText(f"{data['speed']:.1f}")
                self.fleet_table.item(row, 3).setText(f"{int(data['battery'])}%")
                self.fleet_table.item(row, 4).setText(data['status'])

        n = max(1, len(self.usv_fleet))
        self.avg_bat_lbl.setText(f"{int(total_bat / n)}%")
        self.swarm_center_lbl.setText(f"({sum_x / n:.0f}m, {sum_y / n:.0f}m)")

        self._update_inspector()

    def log_event(self, message):
        timestamp = time.strftime("%H:%M:%S")
        self.log_console.append(f"<span style='color:#71717a;'>[{timestamp}]</span> {message}")
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())
