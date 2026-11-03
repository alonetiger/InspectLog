"""Consent dialog displayed before executing intensive stress tests."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class StressTestConsentDialog(QDialog):
    """Explains system load, heat, and fan noise before launching a Full Test."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Consent Required — Intensive Hardware Tests")
        self.setFixedSize(520, 360)
        self.setModal(True)

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Title
        title = QLabel("⚠️ System Stress Test Consent")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #f59e0b;")
        layout.addWidget(title)

        # Information body
        info = QLabel(
            "You are about to launch a Full Hardware Verification scan. "
            "This will execute intensive stress workloads designed to test stability:\n\n"
            "• High CPU & GPU utilization (expect elevated fan noise and heat)\n"
            "• Safe temp-file write-verification across storage to detect fake drives\n"
            "• Memory bit-pattern integrity testing\n"
            "• 60-second battery discharge rate stability sampling\n\n"
            "Safety safeguards:\n"
            "• Automatic thermal emergency cut-off if CPU reaches 95°C\n"
            "• Only safe temporary files are used; your personal files are never touched\n"
            "• All tests can be cancelled at any point"
        )
        info.setWordWrap(True)
        info.setStyleSheet("font-size: 12px; line-height: 140%;")
        layout.addWidget(info)

        layout.addStretch()

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.proceed_btn = QPushButton("I Understand, Start Full Test")
        self.proceed_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.proceed_btn)

        layout.addLayout(btn_layout)
