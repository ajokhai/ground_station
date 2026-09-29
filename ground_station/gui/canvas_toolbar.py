"""
Figma-style Floating Canvas Toolbar for USV Ground Station Radar Canvas.
Provides tool modes: Pan, Waypoint, Geofence/Polygon, Buoy Hazard, Ruler Measure, and Recenter.
"""

from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QButtonGroup, QFrame, QLabel
from PyQt5.QtGui import QFont, QIcon


class CanvasToolbar(QFrame):
    """
    Floating pill-shaped dock anchored over the radar canvas.
    Switches interaction modes so clicks don't accidentally move waypoints.
    """
    tool_changed = pyqtSignal(str)   # 'pan' | 'waypoint' | 'geofence' | 'hazard' | 'measure'
    recenter_clicked = pyqtSignal()
    clear_geofences_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("canvasToolbar")
        self.setFixedHeight(42)

        self.setStyleSheet("""
            QFrame#canvasToolbar {
                background: rgba(18, 18, 22, 0.96);
                border: 1px solid #3f3f46;
                border-radius: 21px;
            }
            QPushButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 15px;
                color: #a1a1aa;
                font-size: 11px;
                font-weight: 600;
                padding: 0 12px;
                height: 30px;
                min-height: 30px;
                max-height: 30px;
            }
            QPushButton:hover {
                background: #27272a;
                color: #fafafa;
            }
            QPushButton:checked {
                background: #0284c7;
                border: 1px solid #38bdf8;
                color: #ffffff;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(7, 5, 7, 5)
        layout.setSpacing(4)


        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        # 1. Pan Tool (Hand - Safe default)
        self.btn_pan = QPushButton("✋ Pan")
        self.btn_pan.setCheckable(True)
        self.btn_pan.setChecked(True)
        self.btn_pan.setToolTip("Pan canvas without moving waypoints (Hot-key: H)")
        self.btn_group.addButton(self.btn_pan)
        layout.addWidget(self.btn_pan)

        # 2. Waypoint Tool (Move Target)
        self.btn_waypoint = QPushButton("🎯 Target")
        self.btn_waypoint.setCheckable(True)
        self.btn_waypoint.setToolTip("Click water to set formation target or drone waypoint (Hot-key: W)")
        self.btn_group.addButton(self.btn_waypoint)
        layout.addWidget(self.btn_waypoint)

        # 3. Geofence / Polygon Boundary Tool
        self.btn_geofence = QPushButton("🛑 Boundary")
        self.btn_geofence.setCheckable(True)
        self.btn_geofence.setToolTip("Draw keep-out zone polygon: click vertices, double-click or close-loop to finish (Hot-key: P)")
        self.btn_group.addButton(self.btn_geofence)
        layout.addWidget(self.btn_geofence)

        # 4. Buoy / Hazard Stamp Tool
        self.btn_hazard = QPushButton("⚠️ Hazard")
        self.btn_hazard.setCheckable(True)
        self.btn_hazard.setToolTip("Click anywhere on water to drop a hazard buoy (Hot-key: B)")
        self.btn_group.addButton(self.btn_hazard)
        layout.addWidget(self.btn_hazard)

        # 5. Measure / Ruler Tool
        self.btn_measure = QPushButton("📏 Ruler")
        self.btn_measure.setCheckable(True)
        self.btn_measure.setToolTip("Click two points to measure distance & compass bearing (Hot-key: M)")
        self.btn_group.addButton(self.btn_measure)
        layout.addWidget(self.btn_measure)

        # Separator
        sep = QLabel("│")
        sep.setStyleSheet("color: #3f3f46; font-size: 13px; padding: 0 1px;")
        layout.addWidget(sep)

        # 6. Recenter View
        self.btn_recenter = QPushButton("↺")
        self.btn_recenter.setToolTip("Reset canvas view to center (Hot-key: R)")
        self.btn_recenter.setFixedWidth(28)
        self.btn_recenter.clicked.connect(self.recenter_clicked.emit)
        layout.addWidget(self.btn_recenter)

        # Signal connections
        self.btn_pan.toggled.connect(lambda c: c and self.tool_changed.emit('pan'))
        self.btn_waypoint.toggled.connect(lambda c: c and self.tool_changed.emit('waypoint'))
        self.btn_geofence.toggled.connect(lambda c: c and self.tool_changed.emit('geofence'))
        self.btn_hazard.toggled.connect(lambda c: c and self.tool_changed.emit('hazard'))
        self.btn_measure.toggled.connect(lambda c: c and self.tool_changed.emit('measure'))

    def set_active_tool(self, tool_name: str):
        """Programmatically switch active tool ('pan', 'waypoint', 'geofence', 'hazard', 'measure')."""
        tool_map = {
            'pan': self.btn_pan,
            'waypoint': self.btn_waypoint,
            'geofence': self.btn_geofence,
            'hazard': self.btn_hazard,
            'measure': self.btn_measure,
        }
        btn = tool_map.get(tool_name.lower())
        if btn:
            btn.setChecked(True)

    def sizeHint(self):
        return QSize(515, 42)


