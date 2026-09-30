"""
Header Toolbar for USV Ground Station.
Provides quick-access mission controls, view style selector, and e-stop.
"""

from PyQt5.QtCore import Qt, QSize, pyqtSignal, QTimer, QPoint
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QComboBox, QListView,
    QLineEdit, QMenu
)
from ground_station.gui.icons import (
    make_play_icon, make_pause_icon, make_rth_icon,
    make_estop_icon, make_sidebar_icon, make_camera_icon
)
from ground_station.core.geocoder import PlaceGeocoder


class PlaceSearchBar(QLineEdit):
    place_selected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("🔍 Search port, coords, or city... (Ctrl+F)")
        self.setFixedWidth(240)
        self.setFixedHeight(26)
        self.setStyleSheet("""
            QLineEdit {
                font-size: 11px;
                padding: 2px 8px;
                background: #141416;
                border: 1px solid #27272a;
                border-radius: 5px;
                color: #fafafa;
            }
            QLineEdit:hover {
                border-color: #3f3f46;
            }
            QLineEdit:focus {
                border-color: #38bdf8;
                background: #18181b;
            }
        """)

        self.geocoder = PlaceGeocoder(self)
        self.geocoder.results_ready.connect(self._on_results)

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(220)
        self._debounce_timer.timeout.connect(self._trigger_search)

        self.textChanged.connect(self._on_text_changed)
        self.returnPressed.connect(self._on_return_pressed)

        self._menu = QMenu(self)
        self._menu.setStyleSheet("""
            QMenu {
                background: #18181b;
                border: 1px solid #27272a;
                border-radius: 6px;
                padding: 4px;
                color: #fafafa;
                font-size: 11px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #27272a;
                color: #38bdf8;
            }
        """)
        self._latest_results = []

    def _on_text_changed(self, text: str):
        if len(text.strip()) >= 2:
            self._debounce_timer.start()
        else:
            self._menu.hide()

    def _trigger_search(self):
        txt = self.text().strip()
        if txt:
            self.geocoder.search(txt)

    def _on_return_pressed(self):
        txt = self.text().strip()
        if not txt:
            return
        coord = PlaceGeocoder.parse_coordinates(txt)
        if coord:
            lat, lon = coord
            self.place_selected.emit({
                "name": f"Coordinate ({lat:.4f}°, {lon:.4f}°)",
                "lat": lat,
                "lon": lon,
                "type": "coordinate"
            })
            self._menu.hide()
            self.clearFocus()
        elif self._latest_results:
            self._select_place(self._latest_results[0])

    def _on_results(self, results: list):
        self._latest_results = results
        if not self.hasFocus() or not results:
            self._menu.hide()
            return

        self._menu.clear()
        for r in results[:6]:
            icon = "⚓" if r.get("type") == "port" else ("🏛️" if r.get("type") == "naval_base" else ("🌊" if r.get("type") in ("canal", "strait") else "📍"))
            region_str = f" ({r['region']})" if r.get("region") else ""
            title = f"{icon}  {r['name']}{region_str}  [{r['lat']:.3f}°, {r['lon']:.3f}°]"
            act = self._menu.addAction(title)
            act.triggered.connect(lambda checked, item=r: self._select_place(item))

        p = self.mapToGlobal(QPoint(0, self.height() + 2))
        self._menu.popup(p)

    def _select_place(self, item: dict):
        self.blockSignals(True)
        self.setText(item['name'])
        self.blockSignals(False)
        self._menu.hide()
        self.clearFocus()
        self.place_selected.emit(item)


class HeaderToolbar(QFrame):
    deploy_clicked = pyqtSignal()
    hold_clicked = pyqtSignal()
    return_home_clicked = pyqtSignal()
    view_mode_changed = pyqtSignal(str)
    operation_mode_changed = pyqtSignal(str)
    emergency_stop_clicked = pyqtSignal()
    sidebar_toggle_clicked = pyqtSignal(bool)
    video_toggle_clicked = pyqtSignal(bool)
    place_selected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("headerToolbar")
        self.setFixedHeight(40)
        self.setStyleSheet("""
            #headerToolbar {
                background: #0c0c0e;
                border-bottom: 1px solid #1c1c1f;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 5, 12, 5)
        layout.setSpacing(6)

        # ── Quick Action Buttons ──
        self.tb_deploy = self._create_icon_btn(
            make_play_icon(QColor("#38bdf8")),
            "Deploy Formation (⌘D)"
        )
        self.tb_deploy.clicked.connect(self.deploy_clicked.emit)
        layout.addWidget(self.tb_deploy)

        self.tb_hold = self._create_icon_btn(
            make_pause_icon(QColor("#fbbf24")),
            "Hold Position (⌘H)"
        )
        self.tb_hold.clicked.connect(self.hold_clicked.emit)
        layout.addWidget(self.tb_hold)

        self.tb_rth = self._create_icon_btn(
            make_rth_icon(QColor("#34d399")),
            "Return to Origin (⌘R)"
        )
        self.tb_rth.clicked.connect(self.return_home_clicked.emit)
        layout.addWidget(self.tb_rth)

        layout.addWidget(self._create_separator())

        # ── Map View Selector ──
        map_lbl = QLabel("Map Style")
        map_lbl.setStyleSheet("color: #71717a; font-size: 11px; font-weight: 500; padding-right: 2px;")
        layout.addWidget(map_lbl)

        self.view_combo = QComboBox()
        self.view_combo.setView(QListView())
        self.view_combo.view().setMinimumWidth(140)
        self.view_combo.addItems(["Grid", "Tactical", "Satellite", "Nautical Chart", "Minimal"])
        self.view_combo.setFixedWidth(130)
        self.view_combo.setToolTip("Map canvas view style")
        self.view_combo.setStyleSheet("""
            QComboBox {
                font-size: 11px;
                padding: 3px 8px;
                min-height: 20px;
                background: #18181b;
                border: 1px solid #27272a;
                border-radius: 5px;
                color: #fafafa;
            }
            QComboBox:hover {
                border-color: #3f3f46;
            }
        """)
        self.view_combo.currentTextChanged.connect(self.view_mode_changed.emit)
        layout.addWidget(self.view_combo)

        layout.addWidget(self._create_separator())

        # ── Mode Selector (Simulation vs External ROS 2 / Hardware) ──
        mode_lbl = QLabel("Mode")
        mode_lbl.setStyleSheet("color: #71717a; font-size: 11px; font-weight: 500; padding-right: 2px;")
        layout.addWidget(mode_lbl)

        self.mode_combo = QComboBox()
        self.mode_combo.setView(QListView())
        self.mode_combo.view().setMinimumWidth(185)
        self.mode_combo.addItems(["🎮 Standalone Simulation", "📡 External ROS 2 / Hardware"])
        self.mode_combo.setFixedWidth(180)
        self.mode_combo.setToolTip("Switch between internal kinematics simulation and live external ROS 2 / Hardware data stream")
        self.mode_combo.setStyleSheet("""
            QComboBox {
                font-size: 11px;
                padding: 3px 8px;
                min-height: 20px;
                background: #18181b;
                border: 1px solid #27272a;
                border-radius: 5px;
                color: #38bdf8;
                font-weight: 600;
            }
            QComboBox:hover {
                border-color: #38bdf8;
            }
        """)
        self.mode_combo.currentTextChanged.connect(self._on_mode_combo_changed)
        layout.addWidget(self.mode_combo)

        # ── Video Toggle Button ──
        self.tb_video = self._create_icon_btn(
            make_camera_icon(QColor("#38bdf8")),
            "Toggle Live Video Feed (⌘V)"
        )
        self.tb_video.setCheckable(True)
        self.tb_video.setChecked(False)
        self.tb_video.clicked.connect(self.video_toggle_clicked.emit)
        layout.addWidget(self.tb_video)
        layout.addStretch()

        # ── Global Place Search Bar ──
        self.search_bar = PlaceSearchBar(self)
        self.search_bar.place_selected.connect(self.place_selected.emit)
        layout.addWidget(self.search_bar)

        layout.addStretch()

        # ── E-Stop Button ──
        self.tb_estop = QPushButton(" STOP")
        self.tb_estop.setIcon(make_estop_icon(QColor("#f87171"), size=24))
        self.tb_estop.setIconSize(QSize(14, 14))
        self.tb_estop.setFixedHeight(28)
        self.tb_estop.setToolTip("Emergency Stop all vehicles (⌘E)")
        self.tb_estop.setStyleSheet("""
            QPushButton {
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 0.5px;
                background: #1c0a0a;
                border: 1px solid #451a1a;
                border-radius: 6px;
                color: #f87171;
                padding: 0 10px;
            }
            QPushButton:hover {
                background: #2b0d0d;
                border-color: #dc2626;
                color: #fca5a5;
            }
            QPushButton:pressed {
                background: #7f1d1d;
                color: #fafafa;
            }
        """)
        self.tb_estop.clicked.connect(self.emergency_stop_clicked.emit)
        layout.addWidget(self.tb_estop)

        layout.addWidget(self._create_separator())

        # ── Sidebar Toggle Button ──
        self.tb_sidebar = self._create_icon_btn(
            make_sidebar_icon(QColor("#a1a1aa")),
            "Toggle Sidebar (⌘1)"
        )
        self.tb_sidebar.setCheckable(True)
        self.tb_sidebar.setChecked(True)
        self.tb_sidebar.clicked.connect(self.sidebar_toggle_clicked.emit)
        layout.addWidget(self.tb_sidebar)

    def _apply_mode_styling(self, mode: str):
        if mode == "EXTERNAL":
            self.mode_combo.setStyleSheet("""
                QComboBox {
                    font-size: 11px;
                    padding: 3px 8px;
                    min-height: 20px;
                    background: #064e3b;
                    border: 1px solid #10b981;
                    border-radius: 5px;
                    color: #34d399;
                    font-weight: 700;
                }
                QComboBox:hover { border-color: #34d399; }
            """)
        else:
            self.mode_combo.setStyleSheet("""
                QComboBox {
                    font-size: 11px;
                    padding: 3px 8px;
                    min-height: 20px;
                    background: #18181b;
                    border: 1px solid #27272a;
                    border-radius: 5px;
                    color: #38bdf8;
                    font-weight: 600;
                }
                QComboBox:hover { border-color: #38bdf8; }
            """)

    def _on_mode_combo_changed(self, text: str):
        mode = "EXTERNAL" if "External" in text else "SIMULATION"
        self._apply_mode_styling(mode)
        self.operation_mode_changed.emit(mode)

    def set_operation_mode(self, mode: str):
        self.mode_combo.blockSignals(True)
        idx = 1 if mode == "EXTERNAL" else 0
        if self.mode_combo.currentIndex() != idx:
            self.mode_combo.setCurrentIndex(idx)
        self._apply_mode_styling(mode)
        self.mode_combo.blockSignals(False)

    def set_view_mode(self, mode_name: str):
        self.view_combo.blockSignals(True)
        idx = self.view_combo.findText(mode_name)
        if idx >= 0:
            self.view_combo.setCurrentIndex(idx)
        self.view_combo.blockSignals(False)

    def set_sidebar_checked(self, checked: bool):
        self.tb_sidebar.blockSignals(True)
        self.tb_sidebar.setChecked(checked)
        self.tb_sidebar.blockSignals(False)

    def set_video_checked(self, checked: bool):
        self.tb_video.blockSignals(True)
        self.tb_video.setChecked(checked)
        self.tb_video.blockSignals(False)

    def _create_icon_btn(self, icon, tooltip: str) -> QPushButton:
        btn = QPushButton()
        btn.setIcon(icon)
        btn.setIconSize(QSize(16, 16))
        btn.setFixedSize(32, 28)
        btn.setToolTip(tooltip)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 5px;
                padding: 0px;
            }
            QPushButton:hover {
                background: #18181b;
                border-color: #27272a;
            }
            QPushButton:pressed {
                background: #27272a;
            }
            QPushButton:checked {
                background: #18181b;
                border-color: #27272a;
            }
        """)
        return btn

    def _create_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setFixedHeight(18)
        sep.setStyleSheet("background: #27272a;")
        return sep
