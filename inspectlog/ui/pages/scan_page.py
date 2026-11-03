"""Scan in-progress page with real-time module status tracking."""

from __future__ import annotations

import time

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from inspectlog.ui.widgets.progress_panel import ProgressPanel


class ScanPage(QWidget):
    """Page displayed while an active scan is executing."""

    scan_cancelled = Signal()
    view_results_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._start_time: float = 0.0

        self._setup_ui()

        # Elapsed timer
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._update_elapsed)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 36, 40, 36)
        layout.setSpacing(20)

        # Header
        top_layout = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(4)

        self.title_lbl = QLabel("Hardware Verification in Progress")
        self.title_lbl.setObjectName("pageTitle")
        title_col.addWidget(self.title_lbl)

        self.time_lbl = QLabel("Elapsed: 00:00")
        self.time_lbl.setObjectName("textSecondary")
        title_col.addWidget(self.time_lbl)
        top_layout.addLayout(title_col)

        top_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel Scan")
        self.cancel_btn.setObjectName("dangerButton")
        self.cancel_btn.clicked.connect(self.scan_cancelled.emit)
        top_layout.addWidget(self.cancel_btn)

        self.view_btn = QPushButton("View Full Report →")
        self.view_btn.setVisible(False)
        self.view_btn.clicked.connect(self.view_results_requested.emit)
        top_layout.addWidget(self.view_btn)

        layout.addLayout(top_layout)

        # Progress Panel
        self.progress_panel = ProgressPanel()
        layout.addWidget(self.progress_panel)

        layout.addStretch()

    def prepare_scan(self, module_defs: list[tuple[str, str, str]]) -> None:
        """Reset and configure the list of modules to test."""
        self.progress_panel.set_modules(module_defs)
        self.progress_panel.set_progress(0)
        self.cancel_btn.setVisible(True)
        self.view_btn.setVisible(False)
        self.title_lbl.setText("Hardware Verification in Progress")
        self._start_time = time.time()
        self._timer.start()

    def update_module_started(self, module_name: str) -> None:
        self.progress_panel.set_module_running(module_name)

    def update_module_completed(self, module_name: str, has_warnings: bool, has_errors: bool) -> None:
        self.progress_panel.set_module_completed(module_name, has_warnings, has_errors)

    def update_progress(self, pct: int) -> None:
        self.progress_panel.set_progress(pct)

    def mark_scan_finished(self) -> None:
        self._timer.stop()
        self.title_lbl.setText("Scan Complete")
        self.cancel_btn.setVisible(False)
        self.view_btn.setVisible(True)

    def _update_elapsed(self) -> None:
        elapsed_sec = int(time.time() - self._start_time)
        mins, secs = divmod(elapsed_sec, 60)
        self.time_lbl.setText(f"Elapsed: {mins:02d}:{secs:02d}")
