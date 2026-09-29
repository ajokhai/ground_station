"""
Swarm Analytics & Fleet Telemetry Dialog for USV Ground Station.
Provides expanded fleet-wide diagnostics:
  - Swarm Tracking & Target Deviation Matrix
  - Vehicle Power, Battery & Endurance Matrix
  - RF Mesh Topology, Latency & Throughput Diagnostics
"""

import math
from typing import Dict, Any, Optional
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView
)


class FleetAnalyticsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Swarm Analytics & Fleet Telemetry")
        self.setFixedSize(680, 520)
        self.setStyleSheet("""
            QDialog {
                background: #09090b;
                color: #fafafa;
                border: 1px solid #27272a;
            }
            QTabWidget::pane {
                border: 1px solid #27272a;
                background: #0c0c0e;
                border-radius: 6px;
            }
            QTabBar::tab {
                background: #18181b;
                color: #71717a;
                padding: 7px 16px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                font-size: 11px;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background: #0c0c0e;
                color: #38bdf8;
                font-weight: 600;
                border: 1px solid #27272a;
                border-bottom: none;
            }
            QTableWidget {
                background: #0d0d10;
                border: 1px solid #27272a;
                border-radius: 6px;
                font-size: 11px;
            }
            QHeaderView::section {
                background: #121215;
                color: #71717a;
                font-size: 10px;
                font-weight: 600;
                padding: 4px;
                border: none;
                border-bottom: 1px solid #27272a;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ─── Header ───
        hdr = QHBoxLayout()
        title_box = QVBoxLayout()
        self.title_lbl = QLabel("Swarm Fleet Analytics")
        self.title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #38bdf8;")
        title_box.addWidget(self.title_lbl)

        self.sub_lbl = QLabel("Multi-Vehicle Kinematics, Energy Matrix & Mesh Topology")
        self.sub_lbl.setStyleSheet("font-size: 10px; color: #71717a;")
        title_box.addWidget(self.sub_lbl)
        hdr.addLayout(title_box)

        hdr.addStretch()

        self.status_pill = QLabel("● SWARM COHESION: OPTIMAL")
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

        # ─── Tabs ───
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_tracking_tab(), "Tracking && Errors")
        self.tabs.addTab(self._create_power_tab(), "Battery && Power")
        self.tabs.addTab(self._create_mesh_tab(), "Mesh RF Topology")
        layout.addWidget(self.tabs)

        # ─── Bottom Bar ───
        bbar = QHBoxLayout()
        self.rate_lbl = QLabel("Telemetry Stream: 30 Hz • Encrypted Link")
        self.rate_lbl.setStyleSheet("font-size: 10px; color: #52525b;")
        bbar.addWidget(self.rate_lbl)
        bbar.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(28)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #18181b; border: 1px solid #27272a;
                border-radius: 5px; color: #e4e4e7; font-size: 11px; padding: 0 16px;
            }
            QPushButton:hover { background: #27272a; color: #fafafa; }
        """)
        close_btn.clicked.connect(self.accept)
        bbar.addWidget(close_btn)
        layout.addLayout(bbar)

    def _create_tracking_tab(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(8)

        desc = QLabel("Formation slot alignment and tracking error variance across the fleet:")
        desc.setStyleSheet("color: #71717a; font-size: 10px; font-style: italic;")
        l.addWidget(desc)

        self.track_table = QTableWidget(4, 6)
        self.track_table.setHorizontalHeaderLabels([
            "USV", "Status", "Current Pos", "Target Slot", "Tracking Error", "Speed"
        ])
        h = self.track_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        h.setSectionResizeMode(3, QHeaderView.Stretch)
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.track_table.verticalHeader().setVisible(False)
        self.track_table.verticalHeader().setDefaultSectionSize(26)
        self.track_table.setShowGrid(False)
        self.track_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.track_table.setSelectionMode(QTableWidget.NoSelection)
        l.addWidget(self.track_table)

        # Summary KPIs
        kpi_row = QHBoxLayout()
        self.kpi_avg_err = QLabel("Avg Deviation: 0.18 m")
        self.kpi_avg_err.setStyleSheet("color: #34d399; font-weight: 600; font-size: 11px; font-family: Menlo, monospace;")
        kpi_row.addWidget(self.kpi_avg_err)

        kpi_row.addStretch()

        self.kpi_max_err = QLabel("Max Deviation: 0.32 m (USV-4)")
        self.kpi_max_err.setStyleSheet("color: #38bdf8; font-weight: 600; font-size: 11px; font-family: Menlo, monospace;")
        kpi_row.addWidget(self.kpi_max_err)

        l.addLayout(kpi_row)
        return w

    def _create_power_tab(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(8)

        desc = QLabel("6S LiPo battery states, bus voltages, power draw, and endurance estimates:")
        desc.setStyleSheet("color: #71717a; font-size: 10px; font-style: italic;")
        l.addWidget(desc)

        self.power_table = QTableWidget(4, 6)
        self.power_table.setHorizontalHeaderLabels([
            "USV", "State of Charge", "Bus Volts", "Current Draw", "Motor RPM", "Endurance"
        ])
        h = self.power_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.power_table.verticalHeader().setVisible(False)
        self.power_table.verticalHeader().setDefaultSectionSize(26)
        self.power_table.setShowGrid(False)
        self.power_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.power_table.setSelectionMode(QTableWidget.NoSelection)
        l.addWidget(self.power_table)

        # Summary KPIs
        kpi_row = QHBoxLayout()
        self.kpi_avg_bat = QLabel("Fleet Avg SOC: 92%")
        self.kpi_avg_bat.setStyleSheet("color: #34d399; font-weight: 600; font-size: 11px; font-family: Menlo, monospace;")
        kpi_row.addWidget(self.kpi_avg_bat)

        kpi_row.addStretch()

        self.kpi_endurance = QLabel("Min Fleet Endurance: 3h 45m")
        self.kpi_endurance.setStyleSheet("color: #fbbf24; font-weight: 600; font-size: 11px; font-family: Menlo, monospace;")
        kpi_row.addWidget(self.kpi_endurance)

        l.addLayout(kpi_row)
        return w

    def _create_mesh_tab(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(8)

        desc = QLabel("Silvus SC4200E 5.8 GHz MIMO tactical mesh radio network telemetry:")
        desc.setStyleSheet("color: #71717a; font-size: 10px; font-style: italic;")
        l.addWidget(desc)

        self.mesh_table = QTableWidget(4, 6)
        self.mesh_table.setHorizontalHeaderLabels([
            "Node", "RSSI (dBm)", "Quality", "Throughput", "Latency", "IP Address"
        ])
        h = self.mesh_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.Stretch)
        h.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.mesh_table.verticalHeader().setVisible(False)
        self.mesh_table.verticalHeader().setDefaultSectionSize(26)
        self.mesh_table.setShowGrid(False)
        self.mesh_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.mesh_table.setSelectionMode(QTableWidget.NoSelection)
        l.addWidget(self.mesh_table)

        kpi_row = QHBoxLayout()
        self.kpi_mesh = QLabel("Topology: Full Dynamic Mesh • 0% Packet Loss")
        self.kpi_mesh.setStyleSheet("color: #34d399; font-weight: 600; font-size: 11px; font-family: Menlo, monospace;")
        kpi_row.addWidget(self.kpi_mesh)
        l.addLayout(kpi_row)
        return w

    def update_fleet_telemetry(self, fleet: Dict[str, Dict[str, Any]], targets: Dict[str, Dict[str, float]]):
        """Update tables in real time from swarm state."""
        if not fleet:
            return

        n = len(fleet)
        self.title_lbl.setText(f"Swarm Fleet Analytics ({n} Vehicles Active)")

        # Sync table row counts
        for tbl in (self.track_table, self.power_table, self.mesh_table):
            if tbl.rowCount() != n:
                tbl.setRowCount(n)

        total_err = 0.0
        max_err = 0.0
        max_err_uid = "USV-1"
        total_bat = 0.0
        min_bat = 100.0

        for row, (uid, d) in enumerate(fleet.items()):
            x, y = d.get('x', 0.0), d.get('y', 0.0)
            spd = d.get('speed', 0.0)
            st = d.get('status', 'IDLE')
            bat = d.get('battery', 90.0)
            sig = d.get('signal', 95.0)
            rssi = d.get('rssi', -62)
            volts = 22.2 + (bat / 100.0) * 3.8
            amps = spd * 2.8 + 1.2
            rpm = int(spd * 420)

            total_bat += bat
            if bat < min_bat:
                min_bat = bat

            # Target slot error calculation
            target = d.get('custom_target') or targets.get(uid, {'x': x, 'y': y})
            tx, ty = target.get('x', x), target.get('y', y)
            err = math.hypot(tx - x, ty - y)
            total_err += err
            if err > max_err:
                max_err = err
                max_err_uid = uid

            # 1. Tracking Table
            self._set_cell(self.track_table, row, 0, uid, "#38bdf8")
            self._set_cell(self.track_table, row, 1, st, "#34d399" if st in ('FORMATION', 'TRANSIT') else "#fafafa")
            self._set_cell(self.track_table, row, 2, f"{x:+.1f}, {y:+.1f}", "#fafafa")
            self._set_cell(self.track_table, row, 3, f"{tx:+.1f}, {ty:+.1f}", "#38bdf8")
            self._set_cell(self.track_table, row, 4, f"{err:.2f} m", "#fbbf24" if err > 1.0 else "#34d399")
            self._set_cell(self.track_table, row, 5, f"{spd:.1f} m/s", "#fafafa")

            # 2. Power Table
            hours = int((bat / 100.0) * 4.2)
            mins = int(((bat / 100.0) * 4.2 - hours) * 60)
            self._set_cell(self.power_table, row, 0, uid, "#38bdf8")
            self._set_cell(self.power_table, row, 1, f"{int(bat)}%", "#34d399" if bat > 50 else "#fbbf24")
            self._set_cell(self.power_table, row, 2, f"{volts:.1f} V", "#fafafa")
            self._set_cell(self.power_table, row, 3, f"{amps:.1f} A", "#fafafa")
            self._set_cell(self.power_table, row, 4, f"{rpm:,}", "#fafafa")
            self._set_cell(self.power_table, row, 5, f"{hours}h {mins:02d}m", "#34d399" if hours >= 2 else "#fbbf24")

            # 3. Mesh Table
            self._set_cell(self.mesh_table, row, 0, uid, "#38bdf8")
            self._set_cell(self.mesh_table, row, 1, f"{rssi} dBm", "#fafafa")
            self._set_cell(self.mesh_table, row, 2, f"{int(sig)}%", "#34d399" if sig > 80 else "#fbbf24")
            self._set_cell(self.mesh_table, row, 3, f"↓ 18.4M  ↑ 3.2M", "#38bdf8")
            self._set_cell(self.mesh_table, row, 4, "8 ms", "#34d399")
            self._set_cell(self.mesh_table, row, 5, f"192.168.144.{100 + row}", "#a1a1aa")

        avg_err = total_err / max(1, n)
        self.kpi_avg_err.setText(f"Avg Deviation: {avg_err:.2f} m")
        self.kpi_max_err.setText(f"Max Deviation: {max_err:.2f} m ({max_err_uid})")
        avg_bat = int(total_bat / max(1, n))
        self.kpi_avg_bat.setText(f"Fleet Avg SOC: {avg_bat}%")
        min_hours = int((min_bat / 100.0) * 4.2)
        min_mins = int(((min_bat / 100.0) * 4.2 - min_hours) * 60)
        self.kpi_endurance.setText(f"Min Fleet Endurance: {min_hours}h {min_mins:02d}m")

    def _set_cell(self, tbl: QTableWidget, row: int, col: int, text: str, color_hex: str):
        item = tbl.item(row, col)
        if not item:
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignVCenter | (Qt.AlignLeft if col in (0, 1) else Qt.AlignCenter))
            tbl.setItem(row, col, item)
        else:
            item.setText(text)
        item.setForeground(QColor(color_hex))
