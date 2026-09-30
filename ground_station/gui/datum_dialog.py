"""
Maritime Operations Area & GPS Datum Selection Dialog.
Enables instant relocation of the Ground Station Datum to oceanic and coastal
testbeds (San Francisco Bay, Monterey, San Diego, Plymouth Sound, Sydney, etc.)
or custom GPS coordinates.
"""

from typing import Optional, Tuple
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QFrame, QWidget, QMessageBox
)

MARITIME_PRESETS = [
    # ── Major Sea Ports & Commercial Harbors ──
    {
        "name": "Port of Rotterdam (Maasvlakte)",
        "region": "Netherlands (North Sea)",
        "category": "Sea Port",
        "icon": "⚓",
        "lat": 51.9500,
        "lon": 4.0500,
        "desc": "Europe's largest seaport, deep-water Maasvlakte container basins & North Sea channel."
    },
    {
        "name": "Port of Singapore (Singapore Strait)",
        "region": "Singapore",
        "category": "Sea Port",
        "icon": "⚓",
        "lat": 1.2644,
        "lon": 103.8200,
        "desc": "Busiest container transshipment hub in the world with dense commercial maritime traffic."
    },
    {
        "name": "Port of Los Angeles & Long Beach",
        "region": "California, USA",
        "category": "Sea Port",
        "icon": "⚓",
        "lat": 33.7200,
        "lon": -118.2200,
        "desc": "San Pedro Bay outer harbor water, breakwater channels, and port approaches."
    },
    {
        "name": "Port of Southampton & The Solent",
        "region": "Hampshire, UK",
        "category": "Sea Port",
        "icon": "⚓",
        "lat": 50.8800,
        "lon": -1.4000,
        "desc": "Major UK automotive & cruise port leading out into the Solent strait."
    },
    {
        "name": "Port of Portsmouth & Naval Base",
        "region": "Hampshire, UK",
        "category": "Sea Port",
        "icon": "⚓",
        "lat": 50.8100,
        "lon": -1.1100,
        "desc": "Historic naval base harbor channel and active surface fleet maneuvering waters."
    },
    {
        "name": "Port of San Diego & Coronado",
        "region": "California, USA",
        "category": "Sea Port",
        "icon": "⚓",
        "lat": 32.6850,
        "lon": -117.1500,
        "desc": "Protected naval and commercial deep-water bay with extensive USV testing corridors."
    },
    {
        "name": "San Francisco Bay & Port of Oakland",
        "region": "California, USA",
        "category": "Sea Port",
        "icon": "⚓",
        "lat": 37.8200,
        "lon": -122.4200,
        "desc": "Deep natural bay channel between Alcatraz Island, San Francisco waterfront, and Oakland docks."
    },
    {
        "name": "Port of Dover (English Channel)",
        "region": "Kent, UK",
        "category": "Sea Port",
        "icon": "⚓",
        "lat": 51.1200,
        "lon": 1.3300,
        "desc": "Busiest passenger and ferry port in Europe fronting the Strait of Dover."
    },
    {
        "name": "Port of Hamburg & Elbe Estuary",
        "region": "Germany",
        "category": "Sea Port",
        "icon": "⚓",
        "lat": 53.5400,
        "lon": 9.9400,
        "desc": "Major tidal river port gateway to the Baltic and North Seas."
    },
    {
        "name": "Port of Dubai / Jebel Ali",
        "region": "United Arab Emirates",
        "category": "Sea Port",
        "icon": "⚓",
        "lat": 25.0100,
        "lon": 55.0600,
        "desc": "Deep-water port in the Arabian Gulf, critical international shipping crossroads."
    },
    {
        "name": "Port of Lagos (Apapa & Tin Can Island)",
        "region": "Lagos, Nigeria (Gulf of Guinea)",
        "category": "Sea Port",
        "icon": "⚓",
        "lat": 6.4400,
        "lon": 3.3650,
        "desc": "Nigeria's primary commercial seaport complex connecting Lagos Harbour to the Atlantic."
    },
    {
        "name": "Port of Onne (Port Harcourt)",
        "region": "Rivers State, Nigeria (Niger Delta)",
        "category": "Sea Port",
        "icon": "⚓",
        "lat": 4.7130,
        "lon": 7.1550,
        "desc": "Major deep-water oil & gas cargo port hub on the Bonny River channel."
    },
    # ── Oceanic & Autonomous Marine Proving Grounds ──
    {
        "name": "Golden Gate & Pacific Ocean Approach",
        "region": "California, USA",
        "category": "Oceanic Gateway",
        "icon": "🌊",
        "lat": 37.8280,
        "lon": -122.4820,
        "desc": "Challenging ocean swell and tidal currents outside the Golden Gate entrance."
    },
    {
        "name": "Monterey Bay Sanctuary (Deep Water)",
        "region": "California, USA",
        "category": "Oceanic Basin",
        "icon": "🌊",
        "lat": 36.6500,
        "lon": -121.8800,
        "desc": "Pristine ocean waters of the Monterey submarine canyon, primary MBARI research testbed."
    },
    {
        "name": "Plymouth Sound Smart Sound Testbed",
        "region": "Devon, UK",
        "category": "Marine Testbed",
        "icon": "🌊",
        "lat": 50.3500,
        "lon": -4.1400,
        "desc": "Premier proving ground for autonomous vessels with instrumented sensor buoys and ranges."
    },
    {
        "name": "Sydney Harbour / Port Jackson",
        "region": "New South Wales, Australia",
        "category": "Harbour & Ocean",
        "icon": "⚓",
        "lat": -33.8568,
        "lon": 151.2153,
        "desc": "Deep natural harbour with busy maritime traffic leading to South Pacific waters."
    },
    {
        "name": "Kaneohe Bay Marine Range",
        "region": "Oahu, Hawaii",
        "category": "Littoral Marine",
        "icon": "🌊",
        "lat": 21.4500,
        "lon": -157.7800,
        "desc": "Tropical coastal and barrier reef waters for littoral USV testing."
    }
]


class MaritimeDatumDialog(QDialog):
    """Modern dark modal for choosing maritime operational areas and configuring GPS Datum."""

    datum_selected = pyqtSignal(str, float, float)  # (name, lat, lon)

    def __init__(self, current_lat: float, current_lon: float, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Maritime Operational Area & GPS Datum")
        self.setFixedSize(560, 480)
        self.setStyleSheet("""
            QDialog {
                background: #09090b;
                border: 1px solid #27272a;
                border-radius: 10px;
                color: #fafafa;
            }
            QLabel { color: #e4e4e7; }
            QLineEdit {
                background: #18181b;
                border: 1px solid #27272a;
                border-radius: 5px;
                padding: 6px 10px;
                color: #38bdf8;
                font-family: monospace;
                font-size: 12px;
                font-weight: 600;
            }
            QLineEdit:focus {
                border-color: #38bdf8;
            }
            QListWidget {
                background: #121216;
                border: 1px solid #27272a;
                border-radius: 6px;
                color: #e4e4e7;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px 10px;
                border-radius: 4px;
                margin-bottom: 2px;
            }
            QListWidget::item:hover {
                background: #1e1e24;
                color: #38bdf8;
            }
            QListWidget::item:selected {
                background: #0284c7;
                color: #ffffff;
                font-weight: 600;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        icon_lbl = QLabel("🌊")
        icon_lbl.setStyleSheet("font-size: 24px;")
        header.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_lbl = QLabel("Maritime Operations Area")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #38bdf8;")
        sub_lbl = QLabel("Select an open water / ocean testbed or enter custom coordinates")
        sub_lbl.setStyleSheet("font-size: 11px; color: #71717a;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header.addLayout(title_box)
        header.addStretch()
        layout.addLayout(header)

        # Filter Category Bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(6)
        filter_lbl = QLabel("<b>Filter:</b>")
        filter_lbl.setStyleSheet("font-size: 11px; color: #a1a1aa;")
        filter_bar.addWidget(filter_lbl)

        btn_style = """
            QPushButton {
                background: #18181b; border: 1px solid #27272a; border-radius: 4px;
                color: #d4d4d8; padding: 3px 10px; font-size: 11px; font-weight: 500;
            }
            QPushButton:hover { background: #27272a; color: #38bdf8; border-color: #38bdf8; }
            QPushButton:checked { background: #0284c7; color: #ffffff; border-color: #38bdf8; font-weight: 700; }
        """

        self.btn_filter_all = QPushButton("All (15)")
        self.btn_filter_all.setCheckable(True)
        self.btn_filter_all.setChecked(True)
        self.btn_filter_all.setStyleSheet(btn_style)
        self.btn_filter_all.clicked.connect(lambda: self._populate_presets("all"))
        filter_bar.addWidget(self.btn_filter_all)

        self.btn_filter_ports = QPushButton("⚓ Sea Ports & Harbors (10)")
        self.btn_filter_ports.setCheckable(True)
        self.btn_filter_ports.setStyleSheet(btn_style)
        self.btn_filter_ports.clicked.connect(lambda: self._populate_presets("port"))
        filter_bar.addWidget(self.btn_filter_ports)

        self.btn_filter_ocean = QPushButton("🌊 Open Ocean & Ranges (5)")
        self.btn_filter_ocean.setCheckable(True)
        self.btn_filter_ocean.setStyleSheet(btn_style)
        self.btn_filter_ocean.clicked.connect(lambda: self._populate_presets("ocean"))
        filter_bar.addWidget(self.btn_filter_ocean)

        filter_bar.addStretch()
        layout.addLayout(filter_bar)

        self.preset_list = QListWidget()
        self._populate_presets("all")
        self.preset_list.itemClicked.connect(self._on_preset_clicked)
        self.preset_list.itemDoubleClicked.connect(self._on_preset_double_clicked)
        layout.addWidget(self.preset_list, stretch=1)

        # Description Card
        self.desc_lbl = QLabel("Select a sea port or ocean zone above to jump directly to open water.")
        self.desc_lbl.setStyleSheet("font-size: 11px; color: #a1a1aa; font-style: italic; padding: 2px 4px;")
        self.desc_lbl.setWordWrap(True)
        layout.addWidget(self.desc_lbl)

        # Coordinates Input Box
        coord_frame = QFrame()
        coord_frame.setStyleSheet("background: #121216; border: 1px solid #27272a; border-radius: 6px; padding: 10px;")
        coord_layout = QHBoxLayout(coord_frame)
        coord_layout.setContentsMargins(6, 6, 6, 6)

        coord_layout.addWidget(QLabel("Latitude (°N):"))
        self.lat_input = QLineEdit(f"{current_lat:.4f}")
        coord_layout.addWidget(self.lat_input)

        coord_layout.addWidget(QLabel("Longitude (°W/E):"))
        self.lon_input = QLineEdit(f"{current_lon:.4f}")
        coord_layout.addWidget(self.lon_input)
        layout.addWidget(coord_frame)

        # Action Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: #18181b; border: 1px solid #27272a; border-radius: 5px;
                color: #a1a1aa; padding: 6px 14px; font-weight: 500; font-size: 12px;
            }
            QPushButton:hover { background: #27272a; color: #fafafa; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        btn_layout.addStretch()

        apply_btn = QPushButton("⚓ Jump to Marine Area")
        apply_btn.setStyleSheet("""
            QPushButton {
                background: #0284c7; border: 1px solid #0369a1; border-radius: 5px;
                color: #ffffff; padding: 6px 18px; font-weight: 700; font-size: 12px;
            }
            QPushButton:hover { background: #0ea5e9; }
        """)
        apply_btn.clicked.connect(self._apply_coordinates)
        btn_layout.addWidget(apply_btn)
        layout.addLayout(btn_layout)

    def _populate_presets(self, filter_type: str = "all"):
        if hasattr(self, 'btn_filter_all'):
            self.btn_filter_all.blockSignals(True)
            self.btn_filter_ports.blockSignals(True)
            self.btn_filter_ocean.blockSignals(True)
            self.btn_filter_all.setChecked(filter_type == "all")
            self.btn_filter_ports.setChecked(filter_type == "port")
            self.btn_filter_ocean.setChecked(filter_type == "ocean")
            self.btn_filter_all.blockSignals(False)
            self.btn_filter_ports.blockSignals(False)
            self.btn_filter_ocean.blockSignals(False)

        self.preset_list.clear()
        for p in MARITIME_PRESETS:
            cat = p.get('category', 'Sea Port')
            is_port = "Port" in cat or "Harbour" in cat
            if filter_type == "port" and not is_port:
                continue
            if filter_type == "ocean" and is_port:
                continue

            icon = p.get('icon', '⚓')
            item = QListWidgetItem(f"{icon} {p['name']}  ·  {p['region']}")
            item.setData(Qt.UserRole, (p['name'], p['lat'], p['lon'], p['desc']))
            self.preset_list.addItem(item)

    def _on_preset_clicked(self, item: QListWidgetItem):
        name, lat, lon, desc = item.data(Qt.UserRole)
        self.lat_input.setText(f"{lat:.4f}")
        self.lon_input.setText(f"{lon:.4f}")
        self.desc_lbl.setText(f"📍 <b>{name}</b>: {desc}")

    def _on_preset_double_clicked(self, item: QListWidgetItem):
        self._on_preset_clicked(item)
        self._apply_coordinates()

    def _apply_coordinates(self):
        try:
            lat = float(self.lat_input.text().strip())
            lon = float(self.lon_input.text().strip())
            if not (-90.0 <= lat <= 90.0):
                raise ValueError("Latitude must be between -90.0 and +90.0 degrees.")
            if not (-180.0 <= lon <= 180.0):
                raise ValueError("Longitude must be between -180.0 and +180.0 degrees.")
        except Exception as e:
            QMessageBox.warning(self, "Invalid Coordinates", f"Please check coordinate values:\n{e}")
            return

        name = "Custom Location"
        sel = self.preset_list.currentItem()
        if sel:
            p_name, p_lat, p_lon, _ = sel.data(Qt.UserRole)
            if abs(lat - p_lat) < 0.0001 and abs(lon - p_lon) < 0.0001:
                name = p_name

        self.datum_selected.emit(name, lat, lon)
        self.accept()
