"""
Aquatic Boat & Sensor Telemetry Dialog for USVs.
Displays comprehensive hydrographic, propulsion, navigation, and hull health readings.
"""

import math
from typing import Optional
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView
)


class SensorDialog(QDialog):
    def __init__(self, usv_id: str, parent=None):
        super().__init__(parent)
        self.usv_id = usv_id
        self.setWindowTitle(f"{usv_id} — Marine Sensor & Telemetry Suite")
        self.setFixedSize(660, 520)
        self.setStyleSheet("""
            QDialog {
                background: #09090b;
                color: #fafafa;
                border: 1px solid #27272a;
                border-radius: 10px;
            }
            QLabel {
                color: #fafafa;
            }
            QTabWidget::pane {
                border: 1px solid #1c1c1f;
                background: #0c0c0e;
                border-radius: 6px;
                padding: 10px;
            }
            QTabBar::tab {
                background: #18181b;
                color: #71717a;
                padding: 6px 8px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 11px;
                font-weight: 500;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #0c0c0e;
                color: #38bdf8;
                font-weight: 600;
                border: 1px solid #1c1c1f;
                border-bottom: none;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        title_box = QVBoxLayout()
        self.title_lbl = QLabel(f"Sensors & Systems — {usv_id}")
        self.title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #38bdf8;")
        title_box.addWidget(self.title_lbl)

        self.sub_lbl = QLabel("High-Rate Hydrographic, Powertrain & Hardware Telemetry")
        self.sub_lbl.setStyleSheet("font-size: 10px; color: #71717a;")
        title_box.addWidget(self.sub_lbl)
        hdr.addLayout(title_box)

        hdr.addStretch()

        self.status_pill = QLabel("● ALL SENSORS NOMINAL")
        self.status_pill.setStyleSheet("""
            background: #064e3b;
            color: #34d399;
            font-size: 10px;
            font-weight: 700;
            padding: 4px 8px;
            border-radius: 4px;
            border: 1px solid #059669;
        """)
        hdr.addWidget(self.status_pill)
        layout.addLayout(hdr)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_hydro_tab(), "Hydro && Env")
        self.tabs.addTab(self._create_propulsion_tab(), "Powertrain")
        self.tabs.addTab(self._create_nav_tab(), "Navigation / IMU")
        self.tabs.addTab(self._create_hull_tab(), "Hull Health")
        self.tabs.addTab(self._create_device_tab(), "Device && Network")
        layout.addWidget(self.tabs)

        # Bottom Bar
        bbar = QHBoxLayout()
        self.rate_lbl = QLabel("Telemetry Stream: 30 Hz • Encrypted Link")
        self.rate_lbl.setStyleSheet("font-size: 10px; color: #52525b;")
        bbar.addWidget(self.rate_lbl)
        bbar.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(28)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #18181b;
                border: 1px solid #27272a;
                border-radius: 5px;
                color: #e4e4e7;
                font-size: 11px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background: #27272a;
                color: #fafafa;
            }
        """)
        close_btn.clicked.connect(self.accept)
        bbar.addWidget(close_btn)
        layout.addLayout(bbar)

    def _create_hydro_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header note
        note = QLabel("Direct comparison between drone onboard sensors (Airmar 200WX / Doppler) and regional weather reports (NOAA #46026):")
        note.setStyleSheet("color: #71717a; font-size: 10px; font-style: italic;")
        layout.addWidget(note)

        # Comparison Table
        self.hydro_table = QTableWidget(7, 4)
        self.hydro_table.setHorizontalHeaderLabels(["Metric", "Drone In-Situ", "Weather Report", "Discrepancy (Δ)"])
        h = self.hydro_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.hydro_table.verticalHeader().setVisible(False)
        self.hydro_table.verticalHeader().setDefaultSectionSize(24)
        self.hydro_table.setShowGrid(False)
        self.hydro_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.hydro_table.setSelectionMode(QTableWidget.NoSelection)
        self.hydro_table.setFixedHeight(202)
        self.hydro_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.hydro_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.hydro_table.setStyleSheet("""
            QTableWidget {
                background: #0d0d10;
                border: 1px solid #27272a;
                border-radius: 6px;
                font-size: 11px;
            }
        """)

        metrics = [
            ("True Wind Speed", "14.2 kn", "11.4 kn", "+2.8 kn ⚠️"),
            ("Wind Direction", "048° NE", "035° NE", "+13°"),
            ("Wind Gust", "18.5 kn", "14.8 kn", "+3.7 kn ⚠️"),
            ("Water Current / Drift", "1.2 kn", "0.8 kn", "+0.4 kn"),
            ("Current Direction", "062° ENE", "050° NE", "+12°"),
            ("Water Temp (SST)", "16.8 °C", "17.2 °C", "-0.4 °C"),
            ("Barometer", "1012.8 hPa", "1014.2 hPa", "-1.4 hPa"),
        ]
        for row, (m, d, r, delta) in enumerate(metrics):
            self.hydro_table.setItem(row, 0, QTableWidgetItem(m))
            self.hydro_table.setItem(row, 1, QTableWidgetItem(d))
            self.hydro_table.setItem(row, 2, QTableWidgetItem(r))
            self.hydro_table.setItem(row, 3, QTableWidgetItem(delta))

        layout.addWidget(self.hydro_table)

        # Additional In-Situ Hydro Acoustics
        g = QGridLayout()
        g.setHorizontalSpacing(16)
        g.setVerticalSpacing(4)
        self.val_depth = self._add_sensor_row(g, 0, "Acoustic Sonar Depth", "18.2 m (Live)", "#38bdf8")
        self.val_salinity = self._add_sensor_row(g, 1, "Water Salinity (CTD)", "34.2 PSU", "#fafafa")
        self.val_turbidity = self._add_sensor_row(g, 2, "Optical Turbidity", "2.1 NTU (Clear)", "#34d399")
        layout.addLayout(g)

        layout.addStretch()
        return w

    def _create_propulsion_tab(self) -> QWidget:
        w = QWidget()
        g = QGridLayout(w)
        g.setContentsMargins(12, 12, 12, 12)
        g.setHorizontalSpacing(16)
        g.setVerticalSpacing(10)

        self.val_m1_rpm = self._add_sensor_row(g, 0, "Port Thruster (M1)", "1,420 RPM", "#fafafa")
        self.val_m2_rpm = self._add_sensor_row(g, 1, "Starboard Thruster (M2)", "1,420 RPM", "#fafafa")
        self.val_esc_temp = self._add_sensor_row(g, 2, "ESC Heatsink Temp", "38.5 °C", "#34d399")
        self.val_bus_v = self._add_sensor_row(g, 3, "Main Bus Voltage", "25.4 V (6S LiPo)", "#34d399")
        self.val_current_draw = self._add_sensor_row(g, 4, "Total Current Draw", "7.8 A", "#fafafa")
        g.setRowStretch(5, 1)
        return w

    def _create_nav_tab(self) -> QWidget:
        w = QWidget()
        g = QGridLayout(w)
        g.setContentsMargins(12, 12, 12, 12)
        g.setHorizontalSpacing(16)
        g.setVerticalSpacing(10)

        self.val_roll_pitch = self._add_sensor_row(g, 0, "Attitude (Roll / Pitch)", "-1.1° / +2.3°", "#fafafa")
        self.val_yaw_rate = self._add_sensor_row(g, 1, "Turn Rate (Gyro Yaw)", "0.0 °/s", "#fafafa")
        self.val_gps_fix = self._add_sensor_row(g, 2, "GNSS Fix Type", "RTK Fixed (3D)", "#34d399")
        self.val_sats = self._add_sensor_row(g, 3, "Satellites Tracked", "18 (GPS+GLO+GAL)", "#fafafa")
        self.val_hdop = self._add_sensor_row(g, 4, "HDOP Precision", "0.7 (Excellent)", "#34d399")
        g.setRowStretch(5, 1)
        return w

    def _create_hull_tab(self) -> QWidget:
        w = QWidget()
        g = QGridLayout(w)
        g.setContentsMargins(12, 12, 12, 12)
        g.setHorizontalSpacing(16)
        g.setVerticalSpacing(10)

        self.val_bilge = self._add_sensor_row(g, 0, "Bilge Water Sensor", "DRY (No Ingress)", "#34d399")
        self.val_hull_temp = self._add_sensor_row(g, 1, "Enclosure Temperature", "24.2 °C", "#fafafa")
        self.val_humidity = self._add_sensor_row(g, 2, "Internal Humidity", "28% RH", "#fafafa")
        self.val_ais = self._add_sensor_row(g, 3, "AIS Transponder", "Class-B Transmitting", "#38bdf8")
        self.val_leak = self._add_sensor_row(g, 4, "Seal Pressure", "101.3 kPa (Sealed)", "#34d399")
        g.setRowStretch(5, 1)
        return w

    def _create_device_tab(self) -> QWidget:
        w = QWidget()
        g = QGridLayout(w)
        g.setContentsMargins(12, 12, 12, 12)
        g.setHorizontalSpacing(16)
        g.setVerticalSpacing(10)

        self._add_sensor_row(g, 0, "Autopilot Firmware", "ArduPilot APM v4.5.1", "#38bdf8")
        self._add_sensor_row(g, 1, "Flight Controller HW", "Pixhawk 6X Pro (STM32H753)", "#fafafa")
        self._add_sensor_row(g, 2, "Onboard Computer", "NVIDIA Jetson Orin Nano (6-Core)", "#fafafa")
        self._add_sensor_row(g, 3, "Compute Load & RAM", "18.4% CPU • 2.4 / 8.0 GB RAM", "#34d399")
        self._add_sensor_row(g, 4, "System Thermals", "CPU 43.8 °C • GPU 41.2 °C (Cool)", "#34d399")
        self._add_sensor_row(g, 5, "Storage & NVMe", "64 GB NVMe SSD (38.2 GB Free)", "#fafafa")
        self._add_sensor_row(g, 6, "Mesh Radio Network", "Silvus SC4200E 5.8GHz MIMO", "#38bdf8")
        self._add_sensor_row(g, 7, "Link Bandwidth & Ping", "14.4 Mbps • 8 ms RTT", "#34d399")
        self._add_sensor_row(g, 8, "Vessel IP Address", f"192.168.144.{100 + (hash(self.usv_id) % 50)}", "#fafafa")
        g.setRowStretch(9, 1)
        return w

    def _add_sensor_row(self, grid: QGridLayout, row: int, label_text: str, val_text: str, val_color: str) -> QLabel:
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        grid.addWidget(lbl, row, 0)

        val = QLabel(val_text)
        val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        val.setStyleSheet(f"color: {val_color}; font-weight: 600; font-family: Menlo, monospace; font-size: 11px;")
        grid.addWidget(val, row, 1)
        return val

    def update_telemetry(self, usv_data: dict, weather_report: Optional[dict] = None):
        """Update sensor values with live simulation data and met comparison."""
        if not usv_data:
            return
        spd = usv_data.get('speed', 0.0)
        hdg_deg = int(math.degrees(usv_data.get('heading', 0.0)) % 360)
        rpm = int(spd * 420)
        bat = usv_data.get('battery', 90.0)
        volts = 22.2 + (bat / 100.0) * 3.8

        self.val_m1_rpm.setText(f"{rpm:,} RPM")
        self.val_m2_rpm.setText(f"{rpm:,} RPM")
        self.val_current_draw.setText(f"{spd * 2.8 + 1.2:.1f} A")
        self.val_bus_v.setText(f"{volts:.1f} V (6S)")
        self.val_yaw_rate.setText(f"{usv_data.get('yaw_rate', 0.0):+.1f} °/s")

        # Update Hydro & Met table if available
        if weather_report and hasattr(self, 'hydro_table'):
            rep = weather_report
            drone_met = usv_data.get('met_data', {})
            d_spd = drone_met.get('wind_spd', rep.get('wind_spd', 11.4) + 2.8)
            d_dir = int(drone_met.get('wind_dir', (rep.get('wind_dir', 35) + 13) % 360))
            d_gst = drone_met.get('wind_gust', rep.get('wind_gust', 14.8) + 3.7)
            d_cur = drone_met.get('current_spd', rep.get('current_spd', 0.8) + 0.4)
            d_cur_dir = int(drone_met.get('current_dir', (rep.get('current_dir', 50) + 12) % 360))
            d_temp = drone_met.get('water_temp', rep.get('water_temp', 17.2) - 0.4)
            d_baro = drone_met.get('barometer', rep.get('barometer', 1014.2) - 1.4)

            r_spd = rep.get('wind_spd', 11.4)
            r_dir = int(rep.get('wind_dir', 35))
            r_gst = rep.get('wind_gust', 14.8)
            r_cur = rep.get('current_spd', 0.8)
            r_cur_dir = int(rep.get('current_dir', 50))
            r_temp = rep.get('water_temp', 17.2)
            r_baro = rep.get('barometer', 1014.2)

            delta_spd = d_spd - r_spd
            delta_dir = (d_dir - r_dir + 180) % 360 - 180
            delta_gst = d_gst - r_gst
            delta_cur = d_cur - r_cur
            delta_cur_dir = (d_cur_dir - r_cur_dir + 180) % 360 - 180
            delta_temp = d_temp - r_temp
            delta_baro = d_baro - r_baro

            items = [
                (f"{d_spd:.1f} kn", f"{r_spd:.1f} kn", f"{delta_spd:+.1f} kn {'⚠️' if abs(delta_spd) > 2.0 else ''}"),
                (f"{d_dir:03d}°", f"{r_dir:03d}°", f"{delta_dir:+d}°"),
                (f"{d_gst:.1f} kn", f"{r_gst:.1f} kn", f"{delta_gst:+.1f} kn {'⚠️' if abs(delta_gst) > 2.5 else ''}"),
                (f"{d_cur:.1f} kn", f"{r_cur:.1f} kn", f"{delta_cur:+.1f} kn"),
                (f"{d_cur_dir:03d}°", f"{r_cur_dir:03d}°", f"{delta_cur_dir:+d}°"),
                (f"{d_temp:.1f} °C", f"{r_temp:.1f} °C", f"{delta_temp:+.1f} °C"),
                (f"{d_baro:.1f} hPa", f"{r_baro:.1f} hPa", f"{delta_baro:+.1f} hPa"),
            ]
            for r_idx, (d_val, r_val, del_val) in enumerate(items):
                it_d = self.hydro_table.item(r_idx, 1)
                if it_d:
                    it_d.setText(d_val)
                it_r = self.hydro_table.item(r_idx, 2)
                if it_r:
                    it_r.setText(r_val)
                it_del = self.hydro_table.item(r_idx, 3)
                if it_del:
                    it_del.setText(del_val)
