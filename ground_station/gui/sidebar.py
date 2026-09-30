"""
Sidebar Control Panel for USV Ground Station.
Includes:
  - Tab 1: Formation configuration, Fleet overview table, and selected USV Inspector
  - Tab 2: Metocean Environment conditions (Wind speed/direction, Water flow/drift, Sonar depth, Sea state),
           GNSS positioning, and Live Vessel Telemetry with popout sensor window.
"""

import math
from typing import Dict, Any, Optional
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QListView, QSlider,
    QTableWidget, QTableWidgetItem, QHeaderView, QWidget,
    QScrollArea
)
from ground_station.gui.theme import STATUS_COLORS
from ground_station.gui.icons import (
    make_play_icon, make_pause_icon, make_target_icon,
    make_close_icon, make_rejoin_icon
)


class SidebarWidget(QFrame):
    formation_type_changed = pyqtSignal(str)
    formation_spacing_changed = pyqtSignal(float)
    formation_heading_changed = pyqtSignal(float)
    deploy_clicked = pyqtSignal()
    swarm_size_changed = pyqtSignal(int)
    usv_selected = pyqtSignal(str)
    deselect_clicked = pyqtSignal()
    focus_usv_clicked = pyqtSignal(str)
    hold_usv_clicked = pyqtSignal(str)
    rejoin_formation_clicked = pyqtSignal(str)
    manual_drive_clicked = pyqtSignal(str)
    view_sensors_clicked = pyqtSignal(str)
    view_fleet_analytics_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarWidget")
        self.setMinimumWidth(260)
        self.setMaximumWidth(480)
        self.setStyleSheet("""
            #sidebarWidget {
                background: #0c0c0e;
                border-left: 1px solid #1c1c1f;
            }
        """)

        self.selected_usv: Optional[str] = None
        self.details_expanded: bool = False
        self.report_met: Dict[str, Any] = {}
        self.drone_mets: Dict[str, Dict[str, Any]] = {}
        self.current_met_mode: str = "⚖️ Compare (Delta)"
        self.current_met_usv: str = "USV-1"

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(12, 10, 12, 10)
        root_layout.setSpacing(8)

        # ─── Top Segmented View Switcher ───
        seg_bar = QFrame()
        seg_bar.setFixedHeight(28)
        seg_bar.setStyleSheet("""
            QFrame {
                background: #18181b;
                border: 1px solid #27272a;
                border-radius: 6px;
            }
        """)
        seg_layout = QHBoxLayout(seg_bar)
        seg_layout.setContentsMargins(2, 2, 2, 2)
        seg_layout.setSpacing(2)

        self.tab_btn_mission = QPushButton("⚓ Mission")
        self.tab_btn_mission.setFixedHeight(22)
        self.tab_btn_mission.clicked.connect(self._show_mission_tab)
        seg_layout.addWidget(self.tab_btn_mission)

        self.tab_btn_env = QPushButton("🌊 Marine && Env")
        self.tab_btn_env.setFixedHeight(22)
        self.tab_btn_env.clicked.connect(self._show_env_tab)
        seg_layout.addWidget(self.tab_btn_env)

        root_layout.addWidget(seg_bar)

        # ─── Panel 1: MISSION CONTAINER ───
        self.mission_container = QWidget()
        m_layout = QVBoxLayout(self.mission_container)
        m_layout.setContentsMargins(0, 0, 0, 0)
        m_layout.setSpacing(5)

        # Formation Section
        m_layout.addWidget(self._section_lbl("FORMATION"))

        self.form_combo = QComboBox()
        self.form_combo.setView(QListView())
        self.form_combo.view().setMinimumWidth(160)
        self.form_combo.addItems(["V-Shape", "Line (Abeam)", "Column (In-line)", "Circle", "Diamond"])
        self.form_combo.setToolTip("Formation geometry pattern")
        self.form_combo.setFixedHeight(26)
        self.form_combo.setStyleSheet("""
            QComboBox {
                background: #18181b;
                border: 1px solid #27272a;
                border-radius: 5px;
                padding: 3px 8px;
                color: #fafafa;
                font-size: 11px;
            }
            QComboBox:hover { border-color: #3f3f46; }
        """)
        self.form_combo.currentTextChanged.connect(self.formation_type_changed.emit)
        m_layout.addWidget(self.form_combo)

        # Spacing and Bearing side-by-side
        params_row = QHBoxLayout()
        params_row.setSpacing(8)

        # Left: Spacing
        spacing_col = QVBoxLayout()
        spacing_col.setSpacing(2)
        row_spacing = QHBoxLayout()
        row_spacing.addWidget(self._muted_lbl("Spacing"))
        row_spacing.addStretch()
        self.spacing_val = QLabel("15m")
        self.spacing_val.setStyleSheet("color: #fafafa; font-size: 10px; font-weight: 600; font-family: Menlo, monospace;")
        row_spacing.addWidget(self.spacing_val)
        spacing_col.addLayout(row_spacing)

        self.spacing_slider = QSlider(Qt.Horizontal)
        self.spacing_slider.setRange(5, 50)
        self.spacing_slider.setValue(15)
        self.spacing_slider.setFixedHeight(16)
        self.spacing_slider.setToolTip("Distance between vehicles (meters)")
        self.spacing_slider.valueChanged.connect(self._on_spacing_slider_changed)
        spacing_col.addWidget(self.spacing_slider)
        params_row.addLayout(spacing_col)

        # Right: Bearing
        hdg_col = QVBoxLayout()
        hdg_col.setSpacing(2)
        row_hdg = QHBoxLayout()
        row_hdg.addWidget(self._muted_lbl("Bearing"))
        row_hdg.addStretch()
        self.heading_val = QLabel("90°")
        self.heading_val.setStyleSheet("color: #fafafa; font-size: 10px; font-weight: 600; font-family: Menlo, monospace;")
        row_hdg.addWidget(self.heading_val)
        hdg_col.addLayout(row_hdg)

        self.heading_slider = QSlider(Qt.Horizontal)
        self.heading_slider.setRange(0, 359)
        self.heading_slider.setValue(90)
        self.heading_slider.setFixedHeight(16)
        self.heading_slider.setToolTip("Formation heading (degrees)")
        self.heading_slider.valueChanged.connect(self._on_heading_slider_changed)
        hdg_col.addWidget(self.heading_slider)
        params_row.addLayout(hdg_col)

        m_layout.addLayout(params_row)

        # Deploy button
        self.deploy_btn = QPushButton("  Deploy Swarm")
        self.deploy_btn.setIcon(make_play_icon(QColor("#09090b"), size=20))
        self.deploy_btn.setIconSize(QSize(13, 13))
        self.deploy_btn.setFixedHeight(28)
        self.deploy_btn.setToolTip("Deploy swarm to target formation (⌘D)")
        self.deploy_btn.setStyleSheet("""
            QPushButton {
                background: #38bdf8;
                color: #09090b;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover { background: #7dd3fc; }
            QPushButton:pressed { background: #0284c7; }
        """)
        self.deploy_btn.clicked.connect(self.deploy_clicked.emit)
        m_layout.addWidget(self.deploy_btn)

        m_layout.addWidget(self._divider())

        # Fleet Section
        fleet_hdr = QHBoxLayout()
        fleet_hdr.addWidget(self._section_lbl("FLEET"))
        fleet_hdr.addStretch()

        size_lbl = QLabel("Size:")
        size_lbl.setStyleSheet("color: #71717a; font-size: 10px; font-weight: 500;")
        fleet_hdr.addWidget(size_lbl)

        self.size_combo = QComboBox()
        self.size_combo.setView(QListView())
        self.size_combo.view().setMinimumWidth(120)
        self.size_combo.setMinimumWidth(80)
        self.size_combo.addItems(["2 USVs", "3 USVs", "4 USVs", "5 USVs", "6 USVs", "8 USVs"])
        self.size_combo.setCurrentText("4 USVs")
        self.size_combo.setToolTip("Change the number of drones in the simulation")
        self.size_combo.setStyleSheet("""
            QComboBox {
                background: #18181b;
                border: 1px solid #27272a;
                border-radius: 4px;
                padding: 1px 6px;
                color: #e4e4e7;
                font-size: 10px;
                font-weight: 500;
                min-height: 18px;
            }
            QComboBox:hover { border-color: #38bdf8; }
        """)
        self.size_combo.currentTextChanged.connect(self._on_size_combo_changed)
        fleet_hdr.addWidget(self.size_combo)
        m_layout.addLayout(fleet_hdr)

        self.fleet_table = QTableWidget(4, 4)
        self.fleet_table.setHorizontalHeaderLabels(["Vehicle", "Status", "Link", "Bat"])
        header = self.fleet_table.horizontalHeader()
        header.setFixedHeight(24)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, 52)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.resizeSection(2, 54)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.resizeSection(3, 46)

        self.fleet_table.verticalHeader().setVisible(False)
        self.fleet_table.verticalHeader().setDefaultSectionSize(24)
        self.fleet_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.fleet_table.setSelectionMode(QTableWidget.SingleSelection)
        self.fleet_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.fleet_table.setShowGrid(False)
        self.fleet_table.setFixedHeight(24 + 4 * 24 + 2)
        self.fleet_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.fleet_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.fleet_table.itemSelectionChanged.connect(self._on_table_selection_changed)
        m_layout.addWidget(self.fleet_table)

        m_layout.addWidget(self._divider())

        # ─── Inspector Card Frame ───
        self.ins_card = QFrame()
        self.ins_card.setObjectName("inspectorCard")
        self.ins_card.setStyleSheet("""
            #inspectorCard {
                background: #111114;
                border: 1px solid #222227;
                border-radius: 8px;
            }
        """)
        ins_card_layout = QVBoxLayout(self.ins_card)
        ins_card_layout.setContentsMargins(10, 7, 10, 7)
        ins_card_layout.setSpacing(4)

        # Inspector Section Header
        ins_header = QHBoxLayout()
        ins_header.setSpacing(6)

        self.ins_title = QLabel("Fleet Overview")
        self.ins_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #38bdf8;")
        ins_header.addWidget(self.ins_title)

        self.deselect_btn = QPushButton()
        self.deselect_btn.setIcon(make_close_icon(QColor("#a1a1aa"), size=16))
        self.deselect_btn.setIconSize(QSize(11, 11))
        self.deselect_btn.setFixedSize(18, 18)
        self.deselect_btn.setToolTip("Unselect drone / Return to Fleet Overview (Esc)")
        self.deselect_btn.setStyleSheet("""
            QPushButton {
                background: #18181b;
                border: 1px solid #27272a;
                border-radius: 9px;
                padding: 0;
            }
            QPushButton:hover { background: #27272a; border-color: #71717a; }
        """)
        self.deselect_btn.clicked.connect(self.deselect_clicked.emit)
        self.deselect_btn.setVisible(False)
        ins_header.addWidget(self.deselect_btn)

        ins_header.addStretch()

        self.ins_status = QLabel("● 4 Online")
        self.ins_status.setStyleSheet("color: #34d399; font-size: 11px; font-weight: 600;")
        ins_header.addWidget(self.ins_status)
        ins_card_layout.addLayout(ins_header)

        # Inspector grid
        self.ins_grid = QGridLayout()
        self.ins_grid.setHorizontalSpacing(8)
        self.ins_grid.setVerticalSpacing(2)
        self.ins_grid.setColumnMinimumWidth(0, 44)

        self.lbl_row0 = self._muted_lbl("Pos")
        self.ins_grid.addWidget(self.lbl_row0, 0, 0)
        self.val_row0 = QLabel("—")
        self.val_row0.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.val_row0.setStyleSheet("color: #fafafa; font-family: Menlo, monospace; font-size: 10px;")
        self.ins_grid.addWidget(self.val_row0, 0, 1)

        self.lbl_row1 = self._muted_lbl("Target")
        self.ins_grid.addWidget(self.lbl_row1, 1, 0)
        self.val_row1 = QLabel("Formation Slot")
        self.val_row1.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.val_row1.setStyleSheet("color: #38bdf8; font-family: Menlo, monospace; font-size: 10px;")
        self.ins_grid.addWidget(self.val_row1, 1, 1)

        self.lbl_row2 = self._muted_lbl("Hdg")
        self.ins_grid.addWidget(self.lbl_row2, 2, 0)
        self.val_row2 = QLabel("—")
        self.val_row2.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.val_row2.setStyleSheet("color: #d4d4d8; font-size: 10px;")
        self.ins_grid.addWidget(self.val_row2, 2, 1)

        self.lbl_row3 = self._muted_lbl("Link")
        self.ins_grid.addWidget(self.lbl_row3, 3, 0)
        self.val_row3 = QLabel("—")
        self.val_row3.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.val_row3.setStyleSheet("color: #34d399; font-weight: 600; font-size: 10px;")
        self.ins_grid.addWidget(self.val_row3, 3, 1)

        self.lbl_row4 = self._muted_lbl("Bat")
        self.ins_grid.addWidget(self.lbl_row4, 4, 0)
        self.val_row4 = QLabel("—")
        self.val_row4.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.val_row4.setStyleSheet("color: #34d399; font-weight: 600; font-size: 10px;")
        self.ins_grid.addWidget(self.val_row4, 4, 1)

        for r in range(5):
            self.ins_grid.setRowMinimumHeight(r, 20)

        ins_card_layout.addLayout(self.ins_grid)

        # ─── Expandable Details Section ───
        self.details_widget = QWidget()
        self.details_layout = QVBoxLayout(self.details_widget)
        self.details_layout.setContentsMargins(0, 4, 0, 4)
        self.details_layout.setSpacing(4)

        det_sep = self._divider()
        self.details_layout.addWidget(det_sep)

        self.details_grid = QGridLayout()
        self.details_grid.setHorizontalSpacing(8)
        self.details_grid.setVerticalSpacing(2)
        self.details_grid.setColumnMinimumWidth(0, 56)

        self.lbl_det0 = self._muted_lbl("Spread")
        self.details_grid.addWidget(self.lbl_det0, 0, 0)
        self.val_det0 = QLabel("—")
        self.val_det0.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.val_det0.setStyleSheet("color: #fafafa; font-family: Menlo, monospace; font-size: 10px;")
        self.details_grid.addWidget(self.val_det0, 0, 1)

        self.lbl_det1 = self._muted_lbl("Form Error")
        self.details_grid.addWidget(self.lbl_det1, 1, 0)
        self.val_det1 = QLabel("—")
        self.val_det1.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.val_det1.setStyleSheet("color: #fafafa; font-family: Menlo, monospace; font-size: 10px;")
        self.details_grid.addWidget(self.val_det1, 1, 1)

        self.lbl_det2 = self._muted_lbl("RF Mesh")
        self.details_grid.addWidget(self.lbl_det2, 2, 0)
        self.val_det2 = QLabel("—")
        self.val_det2.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.val_det2.setStyleSheet("color: #34d399; font-weight: 600; font-size: 10px;")
        self.details_grid.addWidget(self.val_det2, 2, 1)

        self.lbl_det3 = self._muted_lbl("Endurance")
        self.details_grid.addWidget(self.lbl_det3, 3, 0)
        self.val_det3 = QLabel("—")
        self.val_det3.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.val_det3.setStyleSheet("color: #34d399; font-weight: 600; font-size: 10px;")
        self.details_grid.addWidget(self.val_det3, 3, 1)

        for r in range(4):
            self.details_grid.setRowMinimumHeight(r, 20)

        self.details_layout.addLayout(self.details_grid)
        self.details_widget.setVisible(False)

        # ─── Top Action Row on Card ───
        self.card_top_btn_row = QHBoxLayout()
        self.card_top_btn_row.setSpacing(6)

        # Toggle Button: "⌄ View More Details" / "⌃ Collapse Details"
        self.toggle_details_btn = QPushButton("⌄ View More Details")
        self.toggle_details_btn.setFixedHeight(23)
        self.toggle_details_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_details_btn.setToolTip("Toggle expanded telemetry on this card")
        self.toggle_details_btn.setStyleSheet("""
            QPushButton {
                font-size: 10px;
                font-weight: 600;
                background: #141417;
                border: 1px dashed #27272a;
                border-radius: 4px;
                color: #38bdf8;
                padding: 0 8px;
            }
            QPushButton:hover {
                background: #1e293b;
                border: 1px solid #38bdf8;
                color: #7dd3fc;
            }
            QPushButton:pressed {
                background: #0c4a6e;
            }
        """)
        self.toggle_details_btn.clicked.connect(self._toggle_card_details)
        self.card_top_btn_row.addWidget(self.toggle_details_btn, 1)

        self.fleet_analytics_btn = QPushButton("📊 Swarm Analytics ↗")
        self.fleet_analytics_btn.setFixedHeight(23)
        self.fleet_analytics_btn.setToolTip("Open full swarm kinematics, power matrix & mesh telemetry suite")
        self.fleet_analytics_btn.setStyleSheet("""
            QPushButton {
                font-size: 10px; font-weight: 600; background: #18181b;
                border: 1px solid #27272a; border-radius: 4px; color: #38bdf8; padding: 0 6px;
            }
            QPushButton:hover { background: #1e293b; border-color: #38bdf8; color: #7dd3fc; }
        """)
        self.fleet_analytics_btn.clicked.connect(self.view_fleet_analytics_clicked.emit)
        self.card_top_btn_row.addWidget(self.fleet_analytics_btn, 1)

        ins_card_layout.addLayout(self.card_top_btn_row)
        ins_card_layout.addWidget(self.details_widget)

        # Inspector action buttons Row 1 (USV mode)
        self.ins_btns = QHBoxLayout()
        self.ins_btns.setSpacing(4)

        self.focus_btn = QPushButton(" Center")
        self.focus_btn.setIcon(make_target_icon(QColor("#38bdf8"), size=18))
        self.focus_btn.setIconSize(QSize(12, 12))
        self.focus_btn.setFixedHeight(24)
        self.focus_btn.setToolTip("Center radar map on this vehicle")
        self.focus_btn.setStyleSheet("""
            QPushButton {
                font-size: 10px; padding: 0 6px; background: #18181b;
                border: 1px solid #27272a; border-radius: 4px; color: #e4e4e7;
            }
            QPushButton:hover { background: #27272a; border-color: #38bdf8; color: #fafafa; }
        """)
        self.focus_btn.clicked.connect(lambda: self.selected_usv and self.focus_usv_clicked.emit(self.selected_usv))
        self.ins_btns.addWidget(self.focus_btn)

        self.solo_hold_btn = QPushButton(" Hold")
        self.solo_hold_btn.setIcon(make_pause_icon(QColor("#fbbf24"), size=18))
        self.solo_hold_btn.setIconSize(QSize(11, 11))
        self.solo_hold_btn.setFixedHeight(24)
        self.solo_hold_btn.setToolTip("Hold this vehicle in position")
        self.solo_hold_btn.setStyleSheet("""
            QPushButton {
                font-size: 10px; padding: 0 6px; background: #18181b;
                border: 1px solid #27272a; border-radius: 4px; color: #e4e4e7;
            }
            QPushButton:hover { background: #27272a; border-color: #fbbf24; color: #fafafa; }
        """)
        self.solo_hold_btn.clicked.connect(lambda: self.selected_usv and self.hold_usv_clicked.emit(self.selected_usv))
        self.ins_btns.addWidget(self.solo_hold_btn)

        self.rejoin_btn = QPushButton(" Rejoin")
        self.rejoin_btn.setIcon(make_rejoin_icon(QColor("#38bdf8"), size=18))
        self.rejoin_btn.setIconSize(QSize(11, 11))
        self.rejoin_btn.setFixedHeight(24)
        self.rejoin_btn.setToolTip("Cancel individual waypoint & rejoin formation pattern")
        self.rejoin_btn.setStyleSheet("""
            QPushButton {
                font-size: 10px; padding: 0 6px; background: #18181b;
                border: 1px solid #27272a; border-radius: 4px; color: #38bdf8;
            }
            QPushButton:hover { background: #1e293b; border-color: #38bdf8; color: #7dd3fc; }
        """)
        self.rejoin_btn.clicked.connect(lambda: self.selected_usv and self.rejoin_formation_clicked.emit(self.selected_usv))
        self.rejoin_btn.setVisible(False)
        self.ins_btns.addWidget(self.rejoin_btn)

        self.ins_btns.addStretch()
        ins_card_layout.addLayout(self.ins_btns)

        # Inspector action buttons Row 2 (Drive and Expanded Sensors)
        self.ins_btns_row2 = QHBoxLayout()
        self.ins_btns_row2.setSpacing(6)

        self.drive_btn = QPushButton("🎮 Drive")
        self.drive_btn.setFixedHeight(24)
        self.drive_btn.setToolTip("Take manual keyboard control (WASD / Arrows)")
        self.drive_btn.setStyleSheet("""
            QPushButton {
                font-size: 10px; font-weight: 600; background: #18181b;
                border: 1px solid #27272a; border-radius: 4px; color: #e4e4e7; padding: 0 6px;
            }
            QPushButton:hover { background: #27272a; border-color: #38bdf8; color: #fafafa; }
        """)
        self.drive_btn.clicked.connect(lambda: self.selected_usv and self.manual_drive_clicked.emit(self.selected_usv))
        self.ins_btns_row2.addWidget(self.drive_btn, 1)

        self.sensors_btn = QPushButton("📊 Sensors ↗")
        self.sensors_btn.setFixedHeight(24)
        self.sensors_btn.setToolTip("Open full marine sensor telemetry suite (Sonar, Depth, Motors, IMU)")
        self.sensors_btn.setStyleSheet("""
            QPushButton {
                font-size: 10px; font-weight: 600; background: #18181b;
                border: 1px solid #27272a; border-radius: 4px; color: #38bdf8; padding: 0 6px;
            }
            QPushButton:hover { background: #1e293b; border-color: #38bdf8; color: #7dd3fc; }
        """)
        self.sensors_btn.clicked.connect(lambda: self.selected_usv and self.view_sensors_clicked.emit(self.selected_usv))
        self.ins_btns_row2.addWidget(self.sensors_btn, 1)

        ins_card_layout.addLayout(self.ins_btns_row2)

        self.hint_lbl = QLabel("Click map to move formation anchor")
        self.hint_lbl.setStyleSheet("color: #52525b; font-size: 9px; font-style: italic;")
        ins_card_layout.addWidget(self.hint_lbl)

        m_layout.addWidget(self.ins_card)
        m_layout.addStretch()

        self.mission_scroll = QScrollArea()
        self.mission_scroll.setWidgetResizable(True)
        self.mission_scroll.setFrameShape(QFrame.NoFrame)
        self.mission_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.mission_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.mission_scroll.setStyleSheet("QScrollArea { background: #0c0c0e; border: none; }")
        self.mission_scroll.viewport().setStyleSheet("background: #0c0c0e; border: none;")
        self.mission_container.setStyleSheet("background: #0c0c0e;")
        self.mission_scroll.setWidget(self.mission_container)
        root_layout.addWidget(self.mission_scroll)

        # ─── Panel 2: ENVIRONMENT & SENSORS CONTAINER ───
        self.env_container = QWidget()
        e_layout = QVBoxLayout(self.env_container)
        e_layout.setContentsMargins(0, 0, 0, 0)
        e_layout.setSpacing(6)

        # 1. Metocean Conditions
        met_hdr = QHBoxLayout()
        met_hdr.addWidget(self._section_lbl("METOCEAN & WEATHER"))
        met_hdr.addStretch()

        self.met_source_combo = QComboBox()
        self.met_source_combo.setView(QListView())
        self.met_source_combo.view().setMinimumWidth(180)
        self.met_source_combo.setMinimumWidth(135)
        self.met_source_combo.addItems(["⚖️ Compare (Delta)", "🌐 Weather Report", "🤖 Drone In-Situ"])
        self.met_source_combo.setFixedHeight(20)
        self.met_source_combo.setToolTip("Compare regional weather reports vs in-situ drone observations")
        self.met_source_combo.setStyleSheet("""
            QComboBox {
                font-size: 9px;
                font-weight: 600;
                color: #38bdf8;
                padding: 1px 6px;
                min-height: 18px;
            }
        """)
        self.met_source_combo.currentTextChanged.connect(self._on_met_source_changed)
        met_hdr.addWidget(self.met_source_combo)
        e_layout.addLayout(met_hdr)

        # Sub-row with Drone selector and source attribution
        self.met_sub_row = QHBoxLayout()
        self.met_sub_row.setSpacing(6)
        self.met_usv_lbl = QLabel("Drone:")
        self.met_usv_lbl.setStyleSheet("color: #71717a; font-size: 10px; font-weight: 500;")
        self.met_sub_row.addWidget(self.met_usv_lbl)

        self.met_usv_combo = QComboBox()
        self.met_usv_combo.setView(QListView())
        self.met_usv_combo.view().setMinimumWidth(110)
        self.met_usv_combo.setMinimumWidth(75)
        self.met_usv_combo.addItems(["USV-1", "USV-2", "USV-3", "USV-4"])
        self.met_usv_combo.setFixedHeight(18)
        self.met_usv_combo.setStyleSheet("""
            QComboBox {
                font-size: 9px;
                padding: 1px 4px;
                min-height: 16px;
            }
        """)
        self.met_usv_combo.currentTextChanged.connect(self._on_met_usv_changed)
        self.met_sub_row.addWidget(self.met_usv_combo)

        self.met_sub_row.addStretch()

        self.met_source_info = QLabel("NOAA #46026 vs USV-1")
        self.met_source_info.setStyleSheet("color: #52525b; font-size: 9px; font-family: Menlo, monospace;")
        self.met_sub_row.addWidget(self.met_source_info)
        e_layout.addLayout(self.met_sub_row)

        # Discrepancy Alert Banner
        self.met_discrepancy_banner = QLabel("⚠️ Discrepancy: Wind +2.8 kn @ +13° vs Forecast")
        self.met_discrepancy_banner.setStyleSheet("""
            QLabel {
                background: #1c130a;
                border: 1px solid #78350f;
                border-radius: 4px;
                color: #fbbf24;
                font-size: 9px;
                font-weight: 600;
                padding: 3px 6px;
            }
        """)
        e_layout.addWidget(self.met_discrepancy_banner)

        env_grid = QGridLayout()
        env_grid.setHorizontalSpacing(8)
        env_grid.setVerticalSpacing(3)
        env_grid.setColumnMinimumWidth(0, 50)

        self.env_wind = self._add_grid_row(env_grid, 0, "Wind", "11.4 kn @ 035°", "#38bdf8")
        self.env_gust = self._add_grid_row(env_grid, 1, "Gust", "14.8 kn", "#fafafa")
        self.env_current = self._add_grid_row(env_grid, 2, "Current", "0.8 kn @ 050°", "#34d399")
        self.env_depth = self._add_grid_row(env_grid, 3, "Depth", "18.5 m (+0.4m)", "#38bdf8")
        self.env_wave = self._add_grid_row(env_grid, 4, "Sea State", "State 2 (0.3m)", "#fafafa")
        self.env_temp = self._add_grid_row(env_grid, 5, "Water Temp", "17.2 °C", "#fafafa")
        self.env_baro = self._add_grid_row(env_grid, 6, "Barometer", "1014.2 hPa", "#fafafa")
        e_layout.addLayout(env_grid)

        e_layout.addWidget(self._divider())

        # 2. GNSS Positioning
        e_layout.addWidget(self._section_lbl("GNSS & NAVIGATION"))

        gnss_grid = QGridLayout()
        gnss_grid.setHorizontalSpacing(8)
        gnss_grid.setVerticalSpacing(3)
        gnss_grid.setColumnMinimumWidth(0, 50)

        self.env_fix = self._add_grid_row(gnss_grid, 0, "Fix Type", "● RTK Fixed", "#34d399")
        self.env_coords = self._add_grid_row(gnss_grid, 1, "Lat / Lon", "37°46'N, 122°25'W", "#fafafa")
        self.env_sats = self._add_grid_row(gnss_grid, 2, "Satellites", "19 Tracked", "#fafafa")
        self.env_hdop = self._add_grid_row(gnss_grid, 3, "Precision", "HDOP 0.65", "#34d399")
        e_layout.addLayout(gnss_grid)

        e_layout.addWidget(self._divider())

        # 3. Vessel Powertrain & Bilge
        self.vessel_sensor_title = self._section_lbl("VESSEL POWERTRAIN")
        e_layout.addWidget(self.vessel_sensor_title)

        ves_grid = QGridLayout()
        ves_grid.setHorizontalSpacing(8)
        ves_grid.setVerticalSpacing(3)
        ves_grid.setColumnMinimumWidth(0, 50)

        self.env_m1_m2 = self._add_grid_row(ves_grid, 0, "M1/M2 RPM", "1,420 / 1,420", "#fafafa")
        self.env_bus_v = self._add_grid_row(ves_grid, 1, "Bus Volts", "25.4 V (6S)", "#34d399")
        self.env_draw = self._add_grid_row(ves_grid, 2, "Draw", "7.8 A", "#fafafa")
        self.env_bilge = self._add_grid_row(ves_grid, 3, "Bilge Water", "● DRY (Sealed)", "#34d399")
        e_layout.addLayout(ves_grid)

        e_layout.addWidget(self._divider())

        # 4. Equipment & Network Hardware
        e_layout.addWidget(self._section_lbl("EQUIPMENT & NETWORK"))

        eq_grid = QGridLayout()
        eq_grid.setHorizontalSpacing(8)
        eq_grid.setVerticalSpacing(3)
        eq_grid.setColumnMinimumWidth(0, 50)

        self.env_hw = self._add_grid_row(eq_grid, 0, "Hardware", "Jetson Orin • Pixhawk 6X", "#fafafa")
        self.env_fw = self._add_grid_row(eq_grid, 1, "Firmware", "APM v4.5.1 • ROS 2 Jazzy", "#38bdf8")
        self.env_net = self._add_grid_row(eq_grid, 2, "Network", "MIMO Mesh (14.4 Mbps)", "#34d399")
        self.env_ip = self._add_grid_row(eq_grid, 3, "Vessel IP", "192.168.144.101", "#fafafa")
        e_layout.addLayout(eq_grid)

        # Expand button
        self.popout_sensor_btn = QPushButton("↗  Open Full Sensor Suite")
        self.popout_sensor_btn.setFixedHeight(28)
        self.popout_sensor_btn.setToolTip("Open comprehensive 4-tab marine telemetry window")
        self.popout_sensor_btn.setStyleSheet("""
            QPushButton {
                font-size: 10px;
                font-weight: 600;
                background: #18181b;
                border: 1px solid #38bdf8;
                border-radius: 5px;
                color: #38bdf8;
                margin-top: 4px;
            }
            QPushButton:hover {
                background: #1e293b;
                color: #7dd3fc;
            }
        """)
        self.popout_sensor_btn.clicked.connect(lambda: self.view_sensors_clicked.emit(self.selected_usv or "USV-1"))
        e_layout.addWidget(self.popout_sensor_btn)

        e_layout.addStretch()

        self.env_scroll = QScrollArea()
        self.env_scroll.setWidgetResizable(True)
        self.env_scroll.setFrameShape(QFrame.NoFrame)
        self.env_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.env_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.env_scroll.setStyleSheet("QScrollArea { background: #0c0c0e; border: none; }")
        self.env_scroll.viewport().setStyleSheet("background: #0c0c0e; border: none;")
        self.env_container.setStyleSheet("background: #0c0c0e;")
        self.env_scroll.setWidget(self.env_container)
        self.env_scroll.setVisible(False)
        root_layout.addWidget(self.env_scroll)

        self._show_mission_tab()

    # ─── Tab Switching ───

    def _show_mission_tab(self):
        self.mission_scroll.setVisible(True)
        self.env_scroll.setVisible(False)
        self.tab_btn_mission.setStyleSheet("""
            QPushButton {
                font-size: 11px; font-weight: 600; background: #27272a;
                border: none; border-radius: 4px; color: #fafafa;
            }
        """)
        self.tab_btn_env.setStyleSheet("""
            QPushButton {
                font-size: 11px; font-weight: 500; background: transparent;
                border: none; border-radius: 4px; color: #71717a;
            }
            QPushButton:hover { background: #27272a; color: #fafafa; }
        """)

    def _show_env_tab(self):
        self.mission_scroll.setVisible(False)
        self.env_scroll.setVisible(True)
        self.tab_btn_env.setStyleSheet("""
            QPushButton {
                font-size: 11px; font-weight: 600; background: #27272a;
                border: none; border-radius: 4px; color: #38bdf8;
            }
        """)
        self.tab_btn_mission.setStyleSheet("""
            QPushButton {
                font-size: 11px; font-weight: 500; background: transparent;
                border: none; border-radius: 4px; color: #71717a;
            }
            QPushButton:hover { background: #27272a; color: #fafafa; }
        """)

    def _toggle_card_details(self):
        self.details_expanded = not self.details_expanded
        self.details_widget.setVisible(self.details_expanded)
        if self.details_expanded:
            self.toggle_details_btn.setText("⌃ Collapse Details")
            self.toggle_details_btn.setStyleSheet("""
                QPushButton {
                    font-size: 10px;
                    font-weight: 600;
                    background: #18181b;
                    border: 1px solid #3f3f46;
                    border-radius: 4px;
                    color: #a1a1aa;
                    padding: 0 8px;
                }
                QPushButton:hover {
                    background: #27272a;
                    color: #fafafa;
                }
            """)
        else:
            self.toggle_details_btn.setText("⌄ View More Details")
            self.toggle_details_btn.setStyleSheet("""
                QPushButton {
                    font-size: 10px;
                    font-weight: 600;
                    background: #141417;
                    border: 1px dashed #27272a;
                    border-radius: 4px;
                    color: #38bdf8;
                    padding: 0 8px;
                }
                QPushButton:hover {
                    background: #1e293b;
                    border: 1px solid #38bdf8;
                    color: #7dd3fc;
                }
                QPushButton:pressed {
                    background: #0c4a6e;
                }
            """)

    # ─── Public Update Methods ───

    def _on_met_source_changed(self, text: str):
        self.current_met_mode = text
        is_drone_mode = "Drone" in text
        is_compare_mode = "Compare" in text
        self.met_usv_lbl.setVisible(is_drone_mode or is_compare_mode)
        self.met_usv_combo.setVisible(is_drone_mode or is_compare_mode)
        self._render_metocean()

    def _on_met_usv_changed(self, text: str):
        if text:
            self.current_met_usv = text
            self._render_metocean()

    def update_environment_readings(self, ed: Dict[str, Any]):
        """Legacy / single-source update: sets weather report data."""
        self.report_met = ed
        self._render_metocean()

    def update_metocean_data(self, report_data: Dict[str, Any], drone_fleet_mets: Dict[str, Dict[str, Any]]):
        """Update both weather report and drone-reported in-situ meteorological telemetry."""
        if report_data:
            self.report_met = report_data
        if drone_fleet_mets:
            self.drone_mets = drone_fleet_mets
            # Sync USV items in met_usv_combo if count changed
            current_items = [self.met_usv_combo.itemText(i) for i in range(self.met_usv_combo.count())]
            drone_ids = list(drone_fleet_mets.keys())
            if current_items != drone_ids:
                self.met_usv_combo.blockSignals(True)
                self.met_usv_combo.clear()
                self.met_usv_combo.addItems(drone_ids)
                if self.current_met_usv in drone_ids:
                    self.met_usv_combo.setCurrentText(self.current_met_usv)
                self.met_usv_combo.blockSignals(False)

        self._render_metocean()

    def _render_metocean(self):
        rep = self.report_met or {}
        uid = self.current_met_usv
        drone = self.drone_mets.get(uid) or (self.drone_mets.get("USV-1") if self.drone_mets else {}) or {}

        mode = self.current_met_mode

        # Fallbacks for weather report
        rep_w_spd = rep.get('wind_spd', 11.4)
        rep_w_dir = int(rep.get('wind_dir', 35))
        rep_w_gst = rep.get('wind_gust', 14.8)
        rep_c_spd = rep.get('current_spd', 0.8)
        rep_c_dir = int(rep.get('current_dir', 50))
        rep_depth = rep.get('depth', 18.5)
        rep_tide = rep.get('tide', '+0.4m')
        rep_temp = rep.get('water_temp', 17.2)
        rep_baro = rep.get('barometer', 1014.2)
        rep_sea = rep.get('sea_state', 'State 2 (0.3m)')

        # Drone in-situ readings (with local micro-climate discrepancies)
        dr_w_spd = drone.get('wind_spd', rep_w_spd + 2.8)
        dr_w_dir = int(drone.get('wind_dir', (rep_w_dir + 13) % 360))
        dr_w_gst = drone.get('wind_gust', rep_w_gst + 3.7)
        dr_c_spd = drone.get('current_spd', rep_c_spd + 0.4)
        dr_c_dir = int(drone.get('current_dir', (rep_c_dir + 12) % 360))
        dr_depth = drone.get('depth', rep_depth - 0.3)
        dr_temp = drone.get('water_temp', rep_temp - 0.4)
        dr_baro = drone.get('barometer', rep_baro - 1.4)

        # Calculate deltas
        d_spd = dr_w_spd - rep_w_spd
        d_dir = (dr_w_dir - rep_w_dir + 180) % 360 - 180
        d_cur = dr_c_spd - rep_c_spd
        d_baro = dr_baro - rep_baro
        d_temp = dr_temp - rep_temp

        has_discrepancy = abs(d_spd) >= 2.0 or abs(d_dir) >= 10.0 or abs(d_cur) >= 0.3

        station_name = rep.get('station', 'NOAA #46026')
        is_live = rep.get('is_live', False)
        live_icon = "🟢" if is_live else "📡"

        if "Compare" in mode:
            self.met_source_info.setText(f"{live_icon} {station_name} vs {uid}")
            self.met_source_info.setStyleSheet(
                "color: #34d399; font-size: 9px; font-weight: 600; font-family: Menlo, monospace;"
                if is_live else "color: #71717a; font-size: 9px; font-family: Menlo, monospace;"
            )
            self.met_discrepancy_banner.setVisible(True)
            if has_discrepancy:
                self.met_discrepancy_banner.setText(f"⚠️ Discrepancy: Wind {d_spd:+.1f}kn ({d_dir:+d}°) · Drift {d_cur:+.1f}kn")
                self.met_discrepancy_banner.setStyleSheet("""
                    background: #1c130a; border: 1px solid #78350f;
                    border-radius: 4px; color: #fbbf24; font-size: 9px; font-weight: 600; padding: 3px 6px;
                """)
            else:
                self.met_discrepancy_banner.setText("● Report & In-Situ Observations Correlated")
                self.met_discrepancy_banner.setStyleSheet("""
                    background: #052e16; border: 1px solid #065f46;
                    border-radius: 4px; color: #34d399; font-size: 9px; font-weight: 600; padding: 3px 6px;
                """)

            spd_col = "#fbbf24" if abs(d_spd) >= 2.0 else "#34d399"
            self.env_wind.setText(f"{rep_w_spd:.1f} vs {dr_w_spd:.1f}kn ({d_spd:+.1f})")
            self.env_wind.setStyleSheet(f"color: {spd_col}; font-weight: 600; font-family: Menlo, monospace; font-size: 10px;")

            gst_col = "#fbbf24" if abs(dr_w_gst - rep_w_gst) >= 2.5 else "#fafafa"
            self.env_gust.setText(f"{rep_w_gst:.1f} vs {dr_w_gst:.1f}kn ({dr_w_gst - rep_w_gst:+.1f})")
            self.env_gust.setStyleSheet(f"color: {gst_col}; font-weight: 600; font-family: Menlo, monospace; font-size: 10px;")

            cur_col = "#fbbf24" if abs(d_cur) >= 0.3 else "#34d399"
            self.env_current.setText(f"{rep_c_spd:.1f} vs {dr_c_spd:.1f}kn ({d_cur:+.1f})")
            self.env_current.setStyleSheet(f"color: {cur_col}; font-weight: 600; font-family: Menlo, monospace; font-size: 10px;")

            self.env_depth.setText(f"{rep_depth:.1f}m vs {dr_depth:.1f}m ({dr_depth - rep_depth:+.1f})")
            self.env_depth.setStyleSheet("color: #38bdf8; font-weight: 600; font-family: Menlo, monospace; font-size: 10px;")

            self.env_wave.setText(rep_sea)
            self.env_wave.setStyleSheet("color: #fafafa; font-weight: 500; font-size: 10px;")

            self.env_temp.setText(f"{rep_temp:.1f}° vs {dr_temp:.1f}°C ({d_temp:+.1f})")
            self.env_temp.setStyleSheet("color: #fafafa; font-weight: 600; font-family: Menlo, monospace; font-size: 10px;")

            baro_col = "#fbbf24" if abs(d_baro) >= 1.0 else "#fafafa"
            self.env_baro.setText(f"{rep_baro:.1f} vs {dr_baro:.1f} ({d_baro:+.1f})")
            self.env_baro.setStyleSheet(f"color: {baro_col}; font-weight: 600; font-family: Menlo, monospace; font-size: 10px;")

        elif "Weather" in mode:
            self.met_source_info.setText(f"{live_icon} {station_name}")
            self.met_source_info.setStyleSheet(
                "color: #34d399; font-size: 9px; font-weight: 600; font-family: Menlo, monospace;"
                if is_live else "color: #71717a; font-size: 9px; font-family: Menlo, monospace;"
            )
            self.met_discrepancy_banner.setVisible(True)
            self.met_discrepancy_banner.setText(f"{live_icon} {station_name} ({'Real-Time Open-Meteo' if is_live else 'Metocean Baseline'})")
            self.met_discrepancy_banner.setStyleSheet("""
                background: #082f49; border: 1px solid #0369a1;
                border-radius: 4px; color: #38bdf8; font-size: 9px; font-weight: 600; padding: 3px 6px;
            """)
            self.env_wind.setText(f"{rep_w_spd:.1f} kn @ {rep_w_dir:03d}°")
            self.env_wind.setStyleSheet("color: #38bdf8; font-weight: 600; font-family: Menlo, monospace; font-size: 10px;")
            self.env_gust.setText(f"{rep_w_gst:.1f} kn")
            self.env_gust.setStyleSheet("color: #fafafa; font-weight: 600; font-family: Menlo, monospace; font-size: 10px;")
            self.env_current.setText(f"{rep_c_spd:.1f} kn @ {rep_c_dir:03d}°")
            self.env_current.setStyleSheet("color: #34d399; font-weight: 600; font-family: Menlo, monospace; font-size: 10px;")
            self.env_depth.setText(f"{rep_depth:.1f} m ({rep_tide})")
            self.env_depth.setStyleSheet("color: #38bdf8; font-weight: 600; font-family: Menlo, monospace; font-size: 10px;")
            self.env_wave.setText(rep_sea)
            self.env_wave.setStyleSheet("color: #fafafa; font-weight: 500; font-size: 10px;")
            self.env_temp.setText(f"{rep_temp:.1f} °C")
            self.env_temp.setStyleSheet("color: #fafafa; font-weight: 600; font-family: Menlo, monospace; font-size: 10px;")
            self.env_baro.setText(f"{rep_baro:.1f} hPa")
            self.env_baro.setStyleSheet("color: #fafafa; font-weight: 600; font-family: Menlo, monospace; font-size: 10px;")

        else:  # Drone In-Situ
            self.met_source_info.setText(f"{uid} Airmar 200WX")
            self.met_discrepancy_banner.setVisible(True)
            self.met_discrepancy_banner.setText(f"🤖 In-Situ Measured Telemetry from {uid}")
            self.met_discrepancy_banner.setStyleSheet("""
                background: #022c22; border: 1px solid #047857;
                border-radius: 4px; color: #34d399; font-size: 9px; font-weight: 600; padding: 3px 6px;
            """)
            self.env_wind.setText(f"{dr_w_spd:.1f} kn @ {dr_w_dir:03d}°")
            self.env_wind.setStyleSheet("color: #34d399; font-weight: 600; font-family: Menlo, monospace; font-size: 10px;")
            self.env_gust.setText(f"{dr_w_gst:.1f} kn")
            self.env_gust.setStyleSheet("color: #fafafa; font-weight: 600; font-family: Menlo, monospace; font-size: 10px;")
            self.env_current.setText(f"{dr_c_spd:.1f} kn @ {dr_c_dir:03d}°")
            self.env_current.setStyleSheet("color: #38bdf8; font-weight: 600; font-family: Menlo, monospace; font-size: 10px;")
            self.env_depth.setText(f"{dr_depth:.1f} m (Sonar)")
            self.env_depth.setStyleSheet("color: #38bdf8; font-weight: 600; font-family: Menlo, monospace; font-size: 10px;")
            self.env_wave.setText(f"In-Situ Swell (Pitch ±{abs(drone.get('pitch', 1.2)):.1f}°)")
            self.env_wave.setStyleSheet("color: #fafafa; font-weight: 500; font-size: 10px;")
            self.env_temp.setText(f"{dr_temp:.1f} °C (Hull SST)")
            self.env_temp.setStyleSheet("color: #fafafa; font-weight: 600; font-family: Menlo, monospace; font-size: 10px;")
            self.env_baro.setText(f"{dr_baro:.1f} hPa (Sensor)")
            self.env_baro.setStyleSheet("color: #fafafa; font-weight: 600; font-family: Menlo, monospace; font-size: 10px;")

        # GNSS updates from report/drone
        self.env_coords.setText(f"{rep.get('lat_str', '37°46\'N')}, {rep.get('lon_str', '122°25\'W')}")
        self.env_sats.setText(f"{rep.get('sats', 19)} Tracked")
        self.env_hdop.setText(f"HDOP {rep.get('hdop', 0.65):.2f}")

    def update_vessel_sensor_summary(self, uid: str, data: Dict[str, Any]):
        """Update vessel hardware telemetry in environment panel."""
        if not data:
            return
        self.vessel_sensor_title.setText(f"VESSEL POWERTRAIN ({uid})")
        spd = data.get('speed', 0.0)
        rpm = int(spd * 420)
        bat = data.get('battery', 90.0)
        volts = 22.2 + (bat / 100.0) * 3.8
        amps = spd * 2.8 + 1.2

        self.env_m1_m2.setText(f"{rpm:,} / {rpm:,}")
        self.env_bus_v.setText(f"{volts:.1f} V (6S)")
        self.env_draw.setText(f"{amps:.1f} A")

    def set_swarm_size(self, count: int):
        self.size_combo.blockSignals(True)
        idx = self.size_combo.findText(f"{count} USVs")
        if idx >= 0:
            self.size_combo.setCurrentIndex(idx)
        self.size_combo.blockSignals(False)

    def populate_fleet_table(self, fleet: Dict[str, Dict[str, Any]]):
        self.fleet_table.blockSignals(True)
        self.fleet_table.setRowCount(len(fleet))
        h = 24 + len(fleet) * 24 + 2
        self.fleet_table.setFixedHeight(h)
        self.fleet_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.fleet_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        for row_i, (uid, data) in enumerate(fleet.items()):
            self.fleet_table.setRowHeight(row_i, 24)
            item_id = QTableWidgetItem(uid)
            item_st = QTableWidgetItem(data.get('status', 'IDLE'))
            sig = int(data.get('signal', 95))
            item_sig = QTableWidgetItem(f"{sig}%")
            item_sig.setTextAlignment(Qt.AlignCenter)
            item_bat = QTableWidgetItem(f"{int(data.get('battery', 100))}%")
            item_bat.setTextAlignment(Qt.AlignCenter)

            self.fleet_table.setItem(row_i, 0, item_id)
            self.fleet_table.setItem(row_i, 1, item_st)
            self.fleet_table.setItem(row_i, 2, item_sig)
            self.fleet_table.setItem(row_i, 3, item_bat)
        self.fleet_table.blockSignals(False)

    def update_fleet_rows(self, fleet: Dict[str, Dict[str, Any]]):
        for row, (uid, data) in enumerate(fleet.items()):
            if row < self.fleet_table.rowCount():
                item_st = self.fleet_table.item(row, 1)
                if item_st:
                    item_st.setText(data.get('status', 'IDLE'))
                item_sig = self.fleet_table.item(row, 2)
                if item_sig:
                    sig = int(data.get('signal', 95))
                    item_sig.setText(f"{sig}%")
                    item_sig.setTextAlignment(Qt.AlignCenter)
                item_bat = self.fleet_table.item(row, 3)
                if item_bat:
                    item_bat.setText(f"{int(data.get('battery', 0))}%")
                    item_bat.setTextAlignment(Qt.AlignCenter)

    def select_usv(self, usv_id: Optional[str]):
        self.selected_usv = usv_id
        if usv_id:
            self.current_met_usv = usv_id
            self.met_usv_combo.blockSignals(True)
            self.met_usv_combo.setCurrentText(usv_id)
            self.met_usv_combo.blockSignals(False)
            self._render_metocean()
        self.fleet_table.blockSignals(True)
        if usv_id is None:
            self.fleet_table.clearSelection()
        else:
            for row in range(self.fleet_table.rowCount()):
                item = self.fleet_table.item(row, 0)
                if item and item.text() == usv_id:
                    self.fleet_table.selectRow(row)
                    break
        self.fleet_table.blockSignals(False)

    def update_inspector(self, usv_id: str, data: Dict[str, Any]):
        if not data:
            return
        self.selected_usv = usv_id
        self.ins_title.setText(usv_id)
        self.deselect_btn.setVisible(True)

        st = data.get('status', 'IDLE')
        sc = STATUS_COLORS.get(st, '#71717a')
        self.ins_status.setText(f"● {st}")
        self.ins_status.setStyleSheet(f"color: {sc}; font-size: 11px; font-weight: 600;")

        self.lbl_row0.setText("Pos")
        self.val_row0.setText(f"{data.get('x', 0.0):+.1f}, {data.get('y', 0.0):+.1f}")
        self.val_row0.setStyleSheet("color: #fafafa; font-family: Menlo, monospace; font-size: 10px;")

        self.lbl_row1.setText("Target")
        ct = data.get('custom_target')
        if ct:
            self.val_row1.setText(f"{ct['x']:+.1f}, {ct['y']:+.1f}")
            self.val_row1.setStyleSheet("color: #fbbf24; font-family: Menlo, monospace; font-weight: 600; font-size: 10px;")
            self.rejoin_btn.setVisible(True)
        else:
            self.val_row1.setText("Formation Slot")
            self.val_row1.setStyleSheet("color: #38bdf8; font-size: 10px;")
            self.rejoin_btn.setVisible(False)

        self.lbl_row2.setText("Hdg/Spd")
        hdg_deg = int(math.degrees(data.get('heading', 0.0)) % 360)
        dirs = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"]
        octant = dirs[int((hdg_deg + 22.5) // 45) % 8]
        spd = data.get('speed', 0.0)
        self.val_row2.setText(f"{hdg_deg}° {octant} · {spd:.1f} m/s")

        self.lbl_row3.setText("Link")
        sig = int(data.get('signal', 95))
        rssi = int(data.get('rssi', -64))
        sig_col = '#34d399' if sig > 75 else '#fbbf24' if sig > 45 else '#f87171'
        self.val_row3.setText(f"{sig}% ({rssi} dBm)")
        self.val_row3.setStyleSheet(f"color: {sig_col}; font-weight: 600; font-size: 10px;")

        self.lbl_row4.setText("Bat")
        bat = int(data.get('battery', 0))
        bc = '#34d399' if bat > 50 else '#fbbf24' if bat > 20 else '#f87171'
        self.val_row4.setText(f"{bat}%")
        self.val_row4.setStyleSheet(f"color: {bc}; font-weight: 600; font-size: 10px;")

        self.focus_btn.setVisible(True)
        self.solo_hold_btn.setVisible(True)
        self.drive_btn.setVisible(True)
        self.sensors_btn.setVisible(True)
        self.fleet_analytics_btn.setVisible(False)
        self.toggle_details_btn.setVisible(True)
        self.hint_lbl.setText("Click map to move this drone's target")

        if self.details_expanded:
            spd = data.get('speed', 0.0)
            rpm = int(spd * 420)
            bat = data.get('battery', 90.0)
            volts = 22.2 + (bat / 100.0) * 3.8
            amps = spd * 2.8 + 1.2
            watts = volts * amps

            self.lbl_det0.setText("Motors")
            self.val_det0.setText(f"{rpm:,} / {rpm:,} RPM")
            self.val_det0.setStyleSheet("color: #fafafa; font-family: Menlo, monospace; font-size: 10px;")

            self.lbl_det1.setText("Power Bus")
            self.val_det1.setText(f"{volts:.1f}V · {amps:.1f}A ({int(watts)}W)")
            self.val_det1.setStyleSheet("color: #fafafa; font-family: Menlo, monospace; font-size: 10px;")

            self.lbl_det2.setText("Bilge / Temp")
            self.val_det2.setText("Dry (0%) · 38.2°C")
            self.val_det2.setStyleSheet("color: #34d399; font-weight: 600; font-size: 10px;")

            roll = data.get('roll', 0.0)
            pitch = data.get('pitch', 0.0)
            self.lbl_det3.setText("Attitude")
            self.val_det3.setText(f"R:{roll:+.1f}° · P:{pitch:+.1f}°")
            self.val_det3.setStyleSheet("color: #38bdf8; font-family: Menlo, monospace; font-size: 10px;")

        # Also update vessel sensors in environment panel
        self.update_vessel_sensor_summary(usv_id, data)

    def set_manual_drive_active(self, is_active: bool):
        if is_active:
            self.drive_btn.setText("🎮 Driving (WASD)")
            self.drive_btn.setStyleSheet("""
                QPushButton {
                    font-size: 10px; font-weight: 700; background: #78350f;
                    border: 1px solid #f59e0b; border-radius: 4px; color: #fef3c7; padding: 0 6px;
                }
                QPushButton:hover { background: #92400e; }
            """)
        else:
            self.drive_btn.setText("🎮 Drive")
            self.drive_btn.setStyleSheet("""
                QPushButton {
                    font-size: 10px; font-weight: 600; background: #18181b;
                    border: 1px solid #27272a; border-radius: 4px; color: #e4e4e7; padding: 0 6px;
                }
                QPushButton:hover { background: #27272a; border-color: #38bdf8; color: #fafafa; }
            """)

    def show_fleet_overview(self, fleet: Dict[str, Dict[str, Any]], formation_type: str, center: Dict[str, float]):
        self.selected_usv = None
        self.ins_title.setText("Fleet Overview")
        self.deselect_btn.setVisible(False)

        n = len(fleet)
        self.ins_status.setText(f"● {n} Active")
        self.ins_status.setStyleSheet("color: #34d399; font-size: 11px; font-weight: 600;")

        self.lbl_row0.setText("Anchor")
        self.val_row0.setText(f"{center.get('x', 0.0):+.1f}, {center.get('y', 0.0):+.1f}")
        self.val_row0.setStyleSheet("color: #38bdf8; font-family: Menlo, monospace; font-size: 10px;")

        self.lbl_row1.setText("Pattern")
        self.val_row1.setText(formation_type)
        self.val_row1.setStyleSheet("color: #fafafa; font-size: 10px;")

        self.lbl_row2.setText("Status")
        statuses = [d.get('status', 'IDLE') for d in fleet.values()]
        active = sum(1 for s in statuses if s in ('FORMATION', 'TRANSIT'))
        self.val_row2.setText(f"{active}/{n} Moving")

        self.lbl_row3.setText("Avg Link")
        if n > 0:
            avg_sig = int(sum(d.get('signal', 95) for d in fleet.values()) / n)
            avg_rssi = int(sum(d.get('rssi', -64) for d in fleet.values()) / n)
            self.val_row3.setText(f"{avg_sig}% ({avg_rssi} dBm)")
            self.val_row3.setStyleSheet("color: #34d399; font-weight: 600; font-size: 10px;")

        self.lbl_row4.setText("Avg Bat")
        if n > 0:
            avg_bat = int(sum(d.get('battery', 100) for d in fleet.values()) / n)
            self.val_row4.setText(f"{avg_bat}%")
            self.val_row4.setStyleSheet("color: #34d399; font-weight: 600; font-size: 10px;")

        self.focus_btn.setVisible(False)
        self.solo_hold_btn.setVisible(False)
        self.rejoin_btn.setVisible(False)
        self.drive_btn.setVisible(False)
        self.sensors_btn.setVisible(False)
        self.fleet_analytics_btn.setVisible(True)
        self.toggle_details_btn.setVisible(True)
        self.hint_lbl.setText("Click map to move formation anchor")

        if self.details_expanded and fleet:
            cx = center.get('x', 0.0)
            cy = center.get('y', 0.0)
            dists = [math.hypot(d.get('x', 0.0) - cx, d.get('y', 0.0) - cy) for d in fleet.values()]
            max_d = max(dists) if dists else 0.0
            self.lbl_det0.setText("Spread")
            self.val_det0.setText(f"{max_d * 2:.1f} m dia")
            self.val_det0.setStyleSheet("color: #fafafa; font-family: Menlo, monospace; font-size: 10px;")

            speeds = [d.get('speed', 0.0) for d in fleet.values()]
            avg_spd = sum(speeds) / max(1, len(speeds))
            rms_err = 0.18 + avg_spd * 0.08
            self.lbl_det1.setText("Form Error")
            self.val_det1.setText(f"RMS {rms_err:.2f} m")
            self.val_det1.setStyleSheet("color: #34d399; font-family: Menlo, monospace; font-size: 10px;")

            self.lbl_det2.setText("RF Mesh")
            self.val_det2.setText("Peer Mesh · 8 ms")
            self.val_det2.setStyleSheet("color: #38bdf8; font-weight: 600; font-size: 10px;")

            min_bat = min((d.get('battery', 100) for d in fleet.values()), default=100)
            hours = int((min_bat / 100.0) * 4.2)
            mins = int(((min_bat / 100.0) * 4.2 - hours) * 60)
            self.lbl_det3.setText("Endurance")
            self.val_det3.setText(f"~{hours}h {mins:02d}m (Min {int(min_bat)}%)")
            self.val_det3.setStyleSheet("color: #34d399; font-weight: 600; font-size: 10px;")

        # Update environment vessel summary with first available drone
        first_uid = next(iter(fleet.keys()), "USV-1")
        if first_uid in fleet:
            self.update_vessel_sensor_summary(first_uid, fleet[first_uid])

    # ─── Internal Slots ───

    def _on_spacing_slider_changed(self, value: int):
        self.spacing_val.setText(f"{value}m")
        self.formation_spacing_changed.emit(float(value))

    def _on_heading_slider_changed(self, value: int):
        self.heading_val.setText(f"{value}°")
        self.formation_heading_changed.emit(float(value))

    def _on_size_combo_changed(self, text: str):
        try:
            count = int(text.split()[0])
            self.swarm_size_changed.emit(count)
        except Exception:
            pass

    def _on_table_selection_changed(self):
        sel = self.fleet_table.selectedIndexes()
        if sel:
            item = self.fleet_table.item(sel[0].row(), 0)
            if item:
                if item.text() == self.selected_usv:
                    self.deselect_clicked.emit()
                else:
                    self.usv_selected.emit(item.text())

    # ─── Visual Helpers ───

    def _add_grid_row(self, grid: QGridLayout, row: int, label_text: str, val_text: str, val_color: str) -> QLabel:
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #71717a; font-size: 10px;")
        grid.addWidget(lbl, row, 0)

        val = QLabel(val_text)
        val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        val.setStyleSheet(f"color: {val_color}; font-weight: 600; font-family: Menlo, monospace; font-size: 10px;")
        grid.addWidget(val, row, 1)
        return val

    def _section_lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #71717a; font-size: 9px; font-weight: 700; letter-spacing: 1.5px;")
        return lbl

    def _muted_lbl(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #71717a; font-size: 10px;")
        return lbl

    def _divider(self) -> QFrame:
        d = QFrame()
        d.setFixedHeight(1)
        d.setStyleSheet("background: #1c1c1f;")
        return d
