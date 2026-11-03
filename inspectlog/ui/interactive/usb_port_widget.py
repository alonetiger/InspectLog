"""Interactive USB Port insertion and connectivity diagnostic widget."""

from __future__ import annotations

import sys
import time
from typing import Any

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from inspectlog.core.windows.wmi_helpers import safe_wmi_query
from inspectlog.infra.logging import get_logger

logger = get_logger("usb_port_widget")


class USBPortWidget(QWidget):
    """USB Port detection and physical connection testing tab."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._baseline_device_ids: set[str] = set()
        self._verified_ports: list[dict[str, str]] = []

        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(1500)  # Check every 1.5 seconds
        self._poll_timer.timeout.connect(self._check_usb_changes)

        self._init_ui()
        self._take_baseline_snapshot()
        self._poll_timer.start()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        header_row = QHBoxLayout()
        lbl_title = QLabel("USB Port Physical Detection Test")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #E2E8F0;")
        header_row.addWidget(lbl_title)

        header_row.addStretch()

        self.lbl_counter = QLabel("0 USB Ports Tested")
        self.lbl_counter.setStyleSheet("""
            background-color: #1E293B;
            color: #38BDF8;
            font-size: 13px;
            font-weight: 600;
            padding: 6px 14px;
            border-radius: 8px;
            border: 1px solid #334155;
        """)
        header_row.addWidget(self.lbl_counter)
        layout.addLayout(header_row)

        desc = QLabel(
            "Plug a USB drive, mouse, or phone cable into each physical USB port on your machine one by one. "
            "As each port registers data transfer, it will appear in the verified list below."
        )
        desc.setStyleSheet("color: #94A3B8; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Status notification box
        self.notify_box = QFrame()
        self.notify_box.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        notify_layout = QHBoxLayout(self.notify_box)
        self.lbl_notify = QLabel("Waiting for device insertion on any USB port...")
        self.lbl_notify.setStyleSheet("color: #CBD5E1; font-size: 13px; font-weight: 500;")
        notify_layout.addWidget(self.lbl_notify)
        layout.addWidget(self.notify_box)

        # Verified Ports Table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Port #", "Device Detected", "Time Verified"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 8px;
                gridline-color: #1E293B;
            }
            QHeaderView::section {
                background-color: #1E293B;
                color: #94A3B8;
                font-weight: 600;
                padding: 6px;
                border: none;
            }
        """)
        layout.addWidget(self.table, 1)

        # Bottom actions
        btn_row = QHBoxLayout()
        self.btn_manual = QPushButton("+ Manually Confirm Port")
        self.btn_manual.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #E2E8F0;
                font-weight: 600;
                padding: 8px 16px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        self.btn_manual.clicked.connect(self._manual_confirm)
        btn_row.addWidget(self.btn_manual)

        btn_row.addStretch()

        self.btn_pass = QPushButton("✓ Mark USB Ports Passed")
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
        self.btn_pass.clicked.connect(self._mark_passed)
        btn_row.addWidget(self.btn_pass)

        layout.addLayout(btn_row)

    def _take_baseline_snapshot(self) -> None:
        """Record all currently connected USB devices at start of test."""
        devs = safe_wmi_query(
            "Win32_PnPEntity",
            fields=["DeviceID", "Name"],
            where="PNPClass = 'USB' OR DeviceID LIKE 'USB%'",
        )
        for d in devs:
            did = d.get("DeviceID")
            if did:
                self._baseline_device_ids.add(str(did).upper())
        logger.info("USB test initialized with %d baseline devices", len(self._baseline_device_ids))

    def _check_usb_changes(self) -> None:
        """Poll for new USB devices plugged in."""
        current_devs = safe_wmi_query(
            "Win32_PnPEntity",
            fields=["DeviceID", "Name", "Description"],
            where="PNPClass = 'USB' OR DeviceID LIKE 'USB%'",
        )
        for d in current_devs:
            did = str(d.get("DeviceID") or "").upper()
            name = d.get("Name") or d.get("Description") or "USB Device"
            if did and did not in self._baseline_device_ids:
                # New device connected!
                self._baseline_device_ids.add(did)
                self._record_port(name)

    def _record_port(self, device_name: str) -> None:
        port_num = len(self._verified_ports) + 1
        time_str = time.strftime("%H:%M:%S")

        self._verified_ports.append({
            "port": str(port_num),
            "device": device_name,
            "time": time_str,
        })

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(f"Port {port_num}"))
        self.table.setItem(row, 1, QTableWidgetItem(device_name))
        self.table.setItem(row, 2, QTableWidgetItem(time_str))

        self.lbl_counter.setText(f"{len(self._verified_ports)} USB Port(s) Verified")
        self.lbl_counter.setStyleSheet("""
            background-color: #064E3B;
            color: #34D399;
            font-size: 13px;
            font-weight: 600;
            padding: 6px 14px;
            border-radius: 8px;
        """)

        self.lbl_notify.setText(f"✓ New USB device detected: {device_name}")
        self.lbl_notify.setStyleSheet("color: #34D399; font-size: 13px; font-weight: 600;")
        self.notify_box.setStyleSheet("""
            QFrame {
                background-color: #064E3B;
                border: 1px solid #059669;
                border-radius: 8px;
                padding: 10px;
            }
        """)

    def _manual_confirm(self) -> None:
        self._record_port("Manual Port Verification")

    def _mark_passed(self) -> None:
        if not self._verified_ports:
            self._manual_confirm()
        self.lbl_notify.setText("✓ USB ports confirmed functional")

    def closeEvent(self, event) -> None:
        self._poll_timer.stop()
        super().closeEvent(event)

    def get_test_summary(self) -> dict[str, Any]:
        """Return verification outcome for report generation."""
        count = len(self._verified_ports)
        return {
            "verified_ports_count": count,
            "passed": count > 0,
            "ports_list": self._verified_ports,
        }
