"""
Live Video Feed, Audio Monitor, and Network Telemetry Widget.
Provides:
  - FPV / Gimbal Camera view with artificial horizon, compass tape, and reticle
  - Camera modes: EO Daylight, Thermal IR (White-Hot), and Night Vision
  - Hydrophone audio level monitoring with live animated VU decibel meter
  - Real-time Network RF strength, Downlink/Uplink throughput, and latency metrics
  - Picture-in-Picture (PiP) and View Swap capabilities
"""

import math
import time
import random
from typing import Optional
from PyQt5.QtCore import Qt, QPointF, QRectF, QTimer, pyqtSignal, QSize
from PyQt5.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QPolygonF,
    QLinearGradient, QPainterPath, QPixmap
)
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QComboBox, QListView, QWidget
)


class VideoFeedWidget(QFrame):
    swap_view_requested = pyqtSignal()
    close_requested = pyqtSignal()
    detach_requested = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("videoFeedWidget")
        self.resize(320, 215)
        self.setMinimumSize(260, 175)
        self.setStyleSheet("""
            #videoFeedWidget {
                background: #09090b;
                border: 1px solid #27272a;
                border-radius: 8px;
            }
        """)

        # Draggable & Detached state
        self.is_detached = False
        self.custom_pos = None
        self._is_dragging = False
        self._drag_start_global = None
        self._widget_start_pos = None
        self.setMouseTracking(True)

        # State
        self.usv_id = "USV-1"
        self.cam_mode = "Day (EO)"  # "Day (EO)", "Thermal IR", "Night (NVG)"
        self.is_expanded = False
        self.external_frame = None
        self.heading = 0.0
        self.pitch = 1.2
        self.roll = -0.8
        self.speed = 0.0
        self.wave_phase = 0.0

        # Audio state
        self.audio_muted = False
        self.audio_volume = 75
        self.vu_level = -18.0  # dB

        # Network state
        self.signal_pct = 95.0
        self.rssi = -62
        self.downlink_mbps = 18.4
        self.uplink_mbps = 3.2
        self.latency_ms = 8
        self.packet_loss = 0.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        # ─── Top Control Bar ───
        top_bar = QHBoxLayout()
        top_bar.setSpacing(4)

        self.drag_grip = QLabel("⠿")
        self.drag_grip.setStyleSheet("font-size: 13px; color: #71717a; padding-right: 2px;")
        self.drag_grip.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.drag_grip.setToolTip("Click and drag to reposition video feed")
        top_bar.addWidget(self.drag_grip)

        self.cam_title = QLabel("USV-1 CAM")
        self.cam_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #38bdf8;")
        self.cam_title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        top_bar.addWidget(self.cam_title)

        self.mode_combo = QComboBox()
        self.mode_combo.setView(QListView())
        self.mode_combo.view().setMinimumWidth(130)
        self.mode_combo.setMinimumWidth(95)
        self.mode_combo.addItems(["Day (EO)", "Thermal IR", "Night (NVG)"])
        self.mode_combo.setFixedHeight(20)
        self.mode_combo.setStyleSheet("""
            QComboBox {
                background: #18181b;
                border: 1px solid #27272a;
                border-radius: 3px;
                padding: 0 4px;
                color: #e4e4e7;
                font-size: 9px;
                font-weight: 500;
            }
            QComboBox:hover { border-color: #38bdf8; }
        """)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        top_bar.addWidget(self.mode_combo)

        top_bar.addStretch()

        # Detach / Pop-out button (Multi-monitor support)
        self.detach_btn = QPushButton("⤢")
        self.detach_btn.setFixedSize(20, 20)
        self.detach_btn.setToolTip("Detach to external window (drag to another monitor)")
        self.detach_btn.setStyleSheet("""
            QPushButton {
                background: #18181b; border: 1px solid #27272a;
                border-radius: 3px; color: #e4e4e7; font-size: 11px; padding: 0;
            }
            QPushButton:hover { background: #27272a; border-color: #38bdf8; color: #38bdf8; }
        """)
        self.detach_btn.clicked.connect(self._on_detach_clicked)
        top_bar.addWidget(self.detach_btn)

        # Swap button
        self.swap_btn = QPushButton("⇄")
        self.swap_btn.setFixedSize(20, 20)
        self.swap_btn.setToolTip("Swap main map and video view")
        self.swap_btn.setStyleSheet("""
            QPushButton {
                background: #18181b; border: 1px solid #27272a;
                border-radius: 3px; color: #e4e4e7; font-size: 11px; padding: 0;
            }
            QPushButton:hover { background: #27272a; border-color: #38bdf8; color: #38bdf8; }
        """)
        self.swap_btn.clicked.connect(self.swap_view_requested.emit)
        top_bar.addWidget(self.swap_btn)

        # Close button
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setToolTip("Hide video feed")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: #18181b; border: 1px solid #27272a;
                border-radius: 3px; color: #71717a; font-size: 10px; padding: 0;
            }
            QPushButton:hover { background: #27272a; color: #f87171; }
        """)
        self.close_btn.clicked.connect(self.close_requested.emit)
        top_bar.addWidget(self.close_btn)

        layout.addLayout(top_bar)

        # ─── Camera Canvas Widget ───
        self.canvas = _VideoCanvas(self)
        layout.addWidget(self.canvas, stretch=1)

        # ─── Bottom Audio & Network Bar ───
        bot_bar = QHBoxLayout()
        bot_bar.setSpacing(6)

        # Audio mute toggle
        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setFixedSize(20, 18)
        self.mute_btn.setToolTip("Toggle Hydrophone Audio")
        self.mute_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none; font-size: 11px; padding: 0;
            }
        """)
        self.mute_btn.clicked.connect(self._toggle_mute)
        bot_bar.addWidget(self.mute_btn)

        # Live VU Bar
        self.vu_widget = _VUMeterWidget(self)
        self.vu_widget.setFixedSize(48, 12)
        self.vu_widget.setToolTip("Marine Hydrophone Audio Level (dB)")
        bot_bar.addWidget(self.vu_widget)

        bot_bar.addStretch()

        # Network speed & signal stats
        self.net_lbl = QLabel("📶 -62dBm • ↓18.4M ↑3.2M • 8ms")
        self.net_lbl.setStyleSheet("""
            color: #34d399;
            font-size: 9px;
            font-weight: 600;
            font-family: Menlo, monospace;
        """)
        bot_bar.addWidget(self.net_lbl)

        layout.addLayout(bot_bar)

    def set_usv(self, usv_id: str):
        self.usv_id = usv_id
        self.cam_title.setText(f"{usv_id} FPV")
        self.canvas.update()

    def update_telemetry(self, usv_data: dict, net_data: Optional[dict] = None):
        """Update live telemetry from vehicle and network."""
        if usv_data:
            self.speed = usv_data.get('speed', 0.0)
            self.heading = usv_data.get('heading', 0.0)
            self.pitch = usv_data.get('pitch', 1.2)
            self.roll = usv_data.get('roll', -0.8)

        # Audio simulation
        if not self.audio_muted:
            # Cavitation noise increases with speed
            base_db = -24.0 + (self.speed * 2.2)
            jitter = random.uniform(-2.5, 2.5)
            self.vu_level = max(-40.0, min(-2.0, base_db + jitter))
        else:
            self.vu_level = -50.0

        # Network simulation
        if net_data:
            self.downlink_mbps = net_data.get('downlink', 18.4)
            self.uplink_mbps = net_data.get('uplink', 3.2)
            self.latency_ms = net_data.get('latency', 8)
            self.rssi = net_data.get('rssi', -62)
        else:
            if random.random() < 0.08:
                self.downlink_mbps = max(8.0, min(24.0, self.downlink_mbps + random.uniform(-0.6, 0.6)))
                self.latency_ms = max(5, min(22, self.latency_ms + random.randint(-1, 1)))

        self.net_lbl.setText(f"📶 {self.rssi}dBm • ↓{self.downlink_mbps:.1f}M ↑{self.uplink_mbps:.1f}M • {self.latency_ms}ms")
        self.wave_phase = (self.wave_phase + 0.08 + self.speed * 0.04) % (2.0 * math.pi)
        self.canvas.update()
        self.vu_widget.update()

    def set_camera_frame(self, image_bytes: bytes):
        """Update live camera image from external ROS 2 compressed stream."""
        pix = QPixmap()
        if pix.loadFromData(image_bytes):
            self.external_frame = pix
            self.canvas.update()

    def toggle_expanded(self) -> bool:
        """Toggle between PiP (320x215) and full parent-fill geometry."""
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
            self.swap_btn.setText("🗗")
            self.swap_btn.setToolTip("Restore PiP View")
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setMinimumSize(260, 175)
            self.setMaximumSize(16777215, 16777215)
            self.resize(320, 215)
            self.swap_btn.setText("⇄")
            self.swap_btn.setToolTip("Expand to full view")
        return self.is_expanded

    # ─── Mouse Dragging & Repositioning ───

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.is_expanded:
            # Allow dragging anywhere on the top header bar area (top 34 pixels)
            if event.pos().y() <= 34:
                self._is_dragging = True
                self._drag_start_global = event.globalPos()
                self._widget_start_pos = self.pos()
                self.setCursor(Qt.ClosedHandCursor)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, '_is_dragging', False) and (event.buttons() & Qt.LeftButton) and not self.is_expanded:
            delta = event.globalPos() - self._drag_start_global
            if self.is_detached:
                # Freely drag window across any physical monitor/display
                self.move(self._widget_start_pos + delta)
            else:
                target_x = self._widget_start_pos.x() + delta.x()
                target_y = self._widget_start_pos.y() + delta.y()
                if self.parent():
                    pw = self.parent().width()
                    ph = self.parent().height()
                    target_x = max(0, min(target_x, max(0, pw - self.width())))
                    target_y = max(0, min(target_y, max(0, ph - self.height())))
                self.move(target_x, target_y)
                self.custom_pos = (target_x, target_y)
            event.accept()
            return
        elif not self.is_expanded:
            if event.pos().y() <= 34:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if getattr(self, '_is_dragging', False):
            self._is_dragging = False
            self.setCursor(Qt.OpenHandCursor if event.pos().y() <= 34 else Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        # Double-click header bar to toggle full-screen / restore
        if event.button() == Qt.LeftButton and event.pos().y() <= 34:
            self.swap_view_requested.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def leaveEvent(self, event):
        if not getattr(self, '_is_dragging', False):
            self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)

    def _on_detach_clicked(self):
        self.detach_requested.emit(not self.is_detached)

    def set_detached(self, detached: bool, parent=None, initial_pos=None):
        """Detach into independent OS desktop window (multi-monitor) or dock back into canvas."""
        self.is_detached = detached
        if detached:
            self.setParent(None)
            self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint)
            self.setWindowTitle(f"USV Ground Station — {self.usv_id} FPV Video Feed")
            self.detach_btn.setText("↙")
            self.detach_btn.setToolTip("Dock back to radar canvas")
            self.swap_btn.setEnabled(False)
            self.swap_btn.setVisible(False)
            self.drag_grip.setVisible(False)
            self.setMinimumSize(320, 240)
            self.setMaximumSize(16777215, 16777215)
            if initial_pos:
                self.move(initial_pos)
            self.resize(640, 420)
            self.show()
            self.raise_()
            self.activateWindow()
        else:
            self.setParent(parent)
            self.setWindowFlags(Qt.Widget | Qt.SubWindow)
            self.detach_btn.setText("⤢")
            self.detach_btn.setToolTip("Detach to external window (drag to another monitor)")
            self.swap_btn.setEnabled(True)
            self.swap_btn.setVisible(True)
            self.drag_grip.setVisible(True)
            self.setMinimumSize(260, 175)
            self.setMaximumSize(16777215, 16777215)
            self.resize(320, 215)
            self.show()

    def closeEvent(self, event):
        if self.is_detached:
            self.close_requested.emit()
            event.accept()
        else:
            super().closeEvent(event)

    def _toggle_mute(self):
        self.audio_muted = not self.audio_muted
        self.mute_btn.setText("🔇" if self.audio_muted else "🔊")
        self.vu_widget.update()

    def _on_mode_changed(self, text: str):
        self.cam_mode = text
        self.canvas.update()


class _VideoCanvas(QWidget):
    def __init__(self, parent: VideoFeedWidget):
        super().__init__(parent)
        self.feed = parent
        self.setStyleSheet("background: #000000; border-radius: 4px;")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2.0, h / 2.0

        mode = self.feed.cam_mode

        # ── 1. Background (External Image or Synthetic Horizon) ──
        has_ext_frame = getattr(self.feed, 'external_frame', None) and not self.feed.external_frame.isNull()
        if has_ext_frame:
            p.drawPixmap(self.rect(), self.feed.external_frame)
            hud_col = QColor(56, 189, 248) if mode != "Thermal IR" else QColor(250, 204, 21)
        else:
            if mode == "Thermal IR":
                sky_col = QColor(25, 25, 30)
                water_col = QColor(10, 10, 15)
                hud_col = QColor(250, 204, 21)  # Thermal yellow
            elif mode == "Night (NVG)":
                sky_col = QColor(5, 25, 10)
                water_col = QColor(2, 12, 5)
                hud_col = QColor(74, 222, 128)  # Phosphor green
            else:  # Day EO
                sky_col = QColor(15, 35, 55)
                water_col = QColor(10, 25, 40)
                hud_col = QColor(56, 189, 248)  # Cyan HUD

            # Pitch offset for horizon
            pitch_px = cy + math.sin(self.feed.pitch * 0.05) * 30.0

            # Draw Sky
            p.fillRect(0, 0, w, int(pitch_px), sky_col)

            # Draw Ocean Water with Wave swell gradient
            water_grad = QLinearGradient(0, pitch_px, 0, h)
            water_grad.setColorAt(0.0, water_col)
            water_grad.setColorAt(1.0, QColor(water_col.red() // 2, water_col.green() // 2, water_col.blue() // 2))
            p.fillRect(0, int(pitch_px), w, int(h - pitch_px), water_grad)

            # Water swell lines
            p.setPen(QPen(QColor(hud_col.red(), hud_col.green(), hud_col.blue(), 25), 1))
            for i in range(4):
                y_line = pitch_px + (i + 1) * ((h - pitch_px) / 5.0)
                wave_off = math.sin(self.feed.wave_phase + i * 1.5) * 3.0
                p.drawLine(0, int(y_line + wave_off), w, int(y_line + wave_off))

        # ── 2. Top Compass Tape ──
        hdg_deg = int(math.degrees(self.feed.heading) % 360)
        p.setFont(QFont("SF Pro Text", 8, QFont.Bold))
        p.setPen(hud_col)

        tape_y = 16
        for offset in range(-60, 61, 15):
            mark_deg = (hdg_deg + offset) % 360
            mark_x = cx + offset * 2.2
            if 10 < mark_x < w - 10:
                p.drawLine(int(mark_x), tape_y, int(mark_x), tape_y + 4)
                if offset % 30 == 0:
                    dirs = {0: "N", 90: "E", 180: "S", 270: "W"}
                    label = dirs.get(mark_deg, f"{mark_deg:03d}")
                    p.drawText(int(mark_x - 8), tape_y - 3, label)

        # Center heading marker
        p.setPen(QPen(QColor("#f87171"), 1.5))
        p.drawLine(int(cx), tape_y - 2, int(cx), tape_y + 6)

        # ── 3. Pitch Ladder & Center Reticle ──
        p.setPen(QPen(QColor(hud_col.red(), hud_col.green(), hud_col.blue(), 160), 1))

        # Center crosshair reticle
        p.drawLine(int(cx - 14), int(cy), int(cx - 4), int(cy))
        p.drawLine(int(cx + 4), int(cy), int(cx + 14), int(cy))
        p.drawLine(int(cx), int(cy - 14), int(cx), int(cy - 4))
        p.drawLine(int(cx), int(cy + 4), int(cx), int(cy + 14))

        # Pitch bars
        p.drawLine(int(cx - 24), int(pitch_px), int(cx - 10), int(pitch_px))
        p.drawLine(int(cx + 10), int(pitch_px), int(cx + 24), int(pitch_px))

        # ── 4. HUD Telemetry Overlays ──
        p.setFont(QFont("Menlo", 8))
        p.setPen(hud_col)

        # Top-left status
        p.drawText(8, 28, f"{self.feed.usv_id} FPV")
        p.setPen(QColor(248, 113, 113))
        p.drawText(8, 40, "● LIVE")

        # Bottom-left speed & range
        p.setPen(hud_col)
        p.drawText(8, h - 18, f"SOG: {self.feed.speed:.1f} m/s")
        p.drawText(8, h - 8, f"RNG: {35.0 + self.feed.speed * 2.0:.1f} m")

        # Bottom-right stream resolution
        p.drawText(w - 74, h - 8, "1080p60 H.265")


class _VUMeterWidget(QWidget):
    """Animated VU Decibel Meter for Hydrophone Audio."""
    def __init__(self, parent: VideoFeedWidget):
        super().__init__(parent)
        self.feed = parent

    def paintEvent(self, event):
        p = QPainter(self)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(15, 15, 18))

        if self.feed.audio_muted:
            return

        db = self.feed.vu_level  # e.g. -40 to 0 dB
        # Map -40..0 to 0..1
        val = max(0.0, min(1.0, (db + 40.0) / 40.0))
        bar_w = int(w * val)

        grad = QLinearGradient(0, 0, w, 0)
        grad.setColorAt(0.0, QColor(52, 211, 153))   # Emerald
        grad.setColorAt(0.7, QColor(251, 191, 36))   # Amber
        grad.setColorAt(1.0, QColor(248, 113, 113))  # Red

        p.fillRect(0, 0, bar_w, h, grad)
