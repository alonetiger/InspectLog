"""Interactive Microphone input diagnostic with live RMS level meter."""

from __future__ import annotations

import math
import struct
from typing import Any

from PySide6.QtCore import QIODevice, Qt, QTimer
from PySide6.QtMultimedia import (
    QAudioDevice,
    QAudioFormat,
    QAudioSource,
    QMediaDevices,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from inspectlog.infra.logging import get_logger

logger = get_logger("mic_test_widget")


class MicLevelBar(QProgressBar):
    """Custom styled RMS audio level meter."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setRange(0, 100)
        self.setValue(0)
        self.setTextVisible(False)
        self.setFixedHeight(24)
        self.setStyleSheet("""
            QProgressBar {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 6px;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10B981, stop:0.7 #F59E0B, stop:1.0 #EF4444
                );
                border-radius: 5px;
            }
        """)


class MicTestWidget(QWidget):
    """Microphone real-time input verification tab."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._audio_source: QAudioSource | None = None
        self._io_device: QIODevice | None = None
        self._peak_level: int = 0
        self._detected_signal: bool = False

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        header_row = QHBoxLayout()
        lbl_title = QLabel("Microphone Level & Hardware Input Test")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #E2E8F0;")
        header_row.addWidget(lbl_title)
        header_row.addStretch()
        layout.addLayout(header_row)

        desc = QLabel(
            "Select an audio input device below and speak into your laptop microphone. "
            "The live VU meter should bounce in real time as sound is detected."
        )
        desc.setStyleSheet("color: #94A3B8; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Device selector
        dev_row = QHBoxLayout()
        lbl_dev = QLabel("Input Device:")
        lbl_dev.setStyleSheet("color: #CBD5E1; font-weight: 600; font-size: 13px;")
        dev_row.addWidget(lbl_dev)

        self.cmb_devices = QComboBox()
        self.cmb_devices.setStyleSheet("""
            QComboBox {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 280px;
            }
        """)
        self._populate_devices()
        dev_row.addWidget(self.cmb_devices, 1)

        self.btn_toggle = QPushButton("Start Mic")
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: white;
                font-weight: 600;
                padding: 6px 16px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #0369A1; }
        """)
        self.btn_toggle.clicked.connect(self._toggle_monitoring)
        dev_row.addWidget(self.btn_toggle)

        layout.addLayout(dev_row)

        # Meter Card
        meter_card = QFrame()
        meter_card.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        meter_layout = QVBoxLayout(meter_card)
        meter_layout.setSpacing(10)

        meter_header = QHBoxLayout()
        lbl_meter_title = QLabel("Live Audio Input Level (RMS)")
        lbl_meter_title.setStyleSheet("color: #CBD5E1; font-size: 13px; font-weight: 600;")
        meter_header.addWidget(lbl_meter_title)

        meter_header.addStretch()

        self.lbl_level_val = QLabel("0%")
        self.lbl_level_val.setStyleSheet("color: #38BDF8; font-size: 13px; font-weight: 700;")
        meter_header.addWidget(self.lbl_level_val)
        meter_layout.addLayout(meter_header)

        self.meter_bar = MicLevelBar(self)
        meter_layout.addWidget(self.meter_bar)

        stats_row = QHBoxLayout()
        self.lbl_peak = QLabel("Peak Level: 0%")
        self.lbl_peak.setStyleSheet("color: #94A3B8; font-size: 12px;")
        stats_row.addWidget(self.lbl_peak)

        stats_row.addStretch()

        self.lbl_status = QLabel("Status: Microphone idle")
        self.lbl_status.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600;")
        stats_row.addWidget(self.lbl_status)
        meter_layout.addLayout(stats_row)

        layout.addWidget(meter_card)

        # Verification actions
        act_row = QHBoxLayout()
        self.btn_pass = QPushButton("✓ Mark Microphone Verified")
        self.btn_pass.setStyleSheet("""
            QPushButton {
                background-color: #064E3B;
                color: #34D399;
                font-weight: 600;
                padding: 8px 18px;
                border-radius: 6px;
                border: 1px solid #059669;
            }
            QPushButton:hover { background-color: #059669; color: white; }
        """)
        self.btn_pass.clicked.connect(self._mark_verified)
        act_row.addWidget(self.btn_pass)

        act_row.addStretch()

        self.lbl_verdict = QLabel("Verdict: Pending Test")
        self.lbl_verdict.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: 600;")
        act_row.addWidget(self.lbl_verdict)
        layout.addLayout(act_row)

    def _populate_devices(self) -> None:
        try:
            self._devices = QMediaDevices.audioInputs()
            self.cmb_devices.clear()
            for dev in self._devices:
                self.cmb_devices.addItem(dev.description(), dev)
        except Exception as e:
            logger.warning("Failed to list audio inputs: %s", e)

    def _toggle_monitoring(self) -> None:
        if self._audio_source:
            self._stop_monitoring()
        else:
            self._start_monitoring()

    def _start_monitoring(self) -> None:
        idx = self.cmb_devices.currentIndex()
        if idx < 0 or not self._devices:
            return

        device: QAudioDevice = self._devices[idx]
        fmt = device.preferredFormat()

        try:
            self._audio_source = QAudioSource(device, fmt, self)
            self._audio_source.setBufferSize(4096)
            self._io_device = self._audio_source.start()
            if self._io_device:
                self._io_device.readyRead.connect(self._on_audio_data)

            self.btn_toggle.setText("Stop Mic")
            self.btn_toggle.setStyleSheet("""
                QPushButton {
                    background-color: #DC2626;
                    color: white;
                    font-weight: 600;
                    padding: 6px 16px;
                    border-radius: 6px;
                    border: none;
                }
                QPushButton:hover { background-color: #EF4444; }
            """)
            self.lbl_status.setText("Status: Listening...")
            self.lbl_status.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 600;")
        except Exception as e:
            logger.error("Failed to start audio source: %s", e)
            self.lbl_status.setText(f"Status: Error ({e})")

    def _stop_monitoring(self) -> None:
        if self._audio_source:
            try:
                self._audio_source.stop()
            except Exception:
                pass
            self._audio_source = None
            self._io_device = None

        self.btn_toggle.setText("Start Mic")
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: white;
                font-weight: 600;
                padding: 6px 16px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #0369A1; }
        """)
        self.meter_bar.setValue(0)
        self.lbl_level_val.setText("0%")
        self.lbl_status.setText("Status: Stopped")
        self.lbl_status.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600;")

    def _on_audio_data(self) -> None:
        if not self._io_device:
            return

        data = self._io_device.readAll().data()
        if len(data) < 4:
            return

        # Calculate RMS of 16-bit signed shorts
        n_shorts = len(data) // 2
        try:
            shorts = struct.unpack(f"<{n_shorts}h", data[:n_shorts * 2])
            sum_sq = sum(s * s for s in shorts)
            rms = math.sqrt(sum_sq / n_shorts)
            # Scale to 0-100% with slight boost for conversational speech
            pct = min(100, int((rms / 32767.0) * 100 * 3.0))

            self.meter_bar.setValue(pct)
            self.lbl_level_val.setText(f"{pct}%")

            if pct > self._peak_level:
                self._peak_level = pct
                self.lbl_peak.setText(f"Peak Level: {self._peak_level}%")

            if pct > 15 and not self._detected_signal:
                self._detected_signal = True
                self.lbl_status.setText("Status: ✓ Signal Detected (Speech / Sound)")
                self.lbl_status.setStyleSheet("color: #10B981; font-size: 12px; font-weight: 600;")
                self._mark_verified()
        except Exception as e:
            logger.debug("RMS parsing error: %s", e)

    def _mark_verified(self) -> None:
        self.lbl_verdict.setText("Verdict: ✓ Microphone Verified Functional")
        self.lbl_verdict.setStyleSheet("color: #10B981; font-size: 13px; font-weight: 700;")

    def closeEvent(self, event) -> None:
        self._stop_monitoring()
        super().closeEvent(event)

    def get_test_summary(self) -> dict[str, Any]:
        """Return verification outcome for report generation."""
        return {
            "peak_level": self._peak_level,
            "signal_detected": self._detected_signal,
            "passed": self._detected_signal or self._peak_level > 10,
        }
