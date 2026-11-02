"""Home landing page offering Quick Scan and Full Test options."""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hardwareverify.constants import APP_DISPLAY_NAME, APP_VERSION, LOGO_PATH
from hardwareverify.infra.admin import is_admin


class HomePage(QWidget):
    """Initial landing page with scan selection, admin state, and settings."""

    quick_scan_requested = Signal()
    full_test_requested = Signal()
    seller_claims_requested = Signal()
    interactive_diagnostics_requested = Signal()
    theme_toggled = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 36, 40, 36)
        main_layout.setSpacing(28)

        # Top Bar: Title & Theme Toggle
        top_bar = QHBoxLayout()

        if os.path.exists(LOGO_PATH):
            logo_lbl = QLabel()
            pixmap = QPixmap(LOGO_PATH).scaledToHeight(48, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pixmap)
            top_bar.addWidget(logo_lbl)
            top_bar.addSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        title_lbl = QLabel(APP_DISPLAY_NAME)
        title_lbl.setObjectName("pageTitle")
        title_col.addWidget(title_lbl)

        sub_lbl = QLabel("Verify component authenticity, battery wear, storage health, and detect spoofed hardware.")
        sub_lbl.setObjectName("pageSubtitle")
        title_col.addWidget(sub_lbl)
        top_bar.addLayout(title_col)

        top_bar.addStretch()

        # Admin Badge
        admin_ok = is_admin()
        admin_badge = QLabel("🛡️ Administrator" if admin_ok else "⚠️ Standard User (Some checks limited)")
        admin_badge.setStyleSheet(
            "background-color: #064e3b; color: #34d399; padding: 6px 12px; border-radius: 6px; font-weight: 600;"
            if admin_ok
            else "background-color: #78350f; color: #fbbf24; padding: 6px 12px; border-radius: 6px; font-weight: 600;"
        )
        top_bar.addWidget(admin_badge)

        # Theme Toggle Button
        self.theme_btn = QPushButton("🌙 / ☀️")
        self.theme_btn.setObjectName("secondaryButton")
        self.theme_btn.setFixedWidth(65)
        self.theme_btn.clicked.connect(self.theme_toggled.emit)
        top_bar.addWidget(self.theme_btn)

        main_layout.addLayout(top_bar)

        # Scan Cards Area
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(24)

        # Quick Scan Card
        quick_card = QFrame()
        quick_card.setObjectName("cardFrame")
        qc_layout = QVBoxLayout(quick_card)
        qc_layout.setContentsMargins(28, 28, 28, 28)
        qc_layout.setSpacing(16)

        qc_icon = QLabel("⚡")
        qc_icon.setStyleSheet("font-size: 36px;")
        qc_layout.addWidget(qc_icon)

        qc_title = QLabel("Quick Scan")
        qc_title.setStyleSheet("font-size: 20px; font-weight: 700;")
        qc_layout.addWidget(qc_title)

        qc_desc = QLabel(
            "Recommended for fast inspection when meeting a seller. Takes ~2 minutes.\n\n"
            "✓ System Serial & BIOS authenticity\n"
            "✓ Battery wear % and cycle count\n"
            "✓ Drive SMART health and lifetime power-on hours\n"
            "✓ RAM capacity, rated vs actual speeds\n"
            "✓ CPU core count and spoof check\n"
            "✓ Windows activation & Secure Boot / TPM"
        )
        qc_desc.setStyleSheet("color: #94a3b8; line-height: 140%;")
        qc_layout.addWidget(qc_desc)

        qc_layout.addStretch()

        self.quick_btn = QPushButton("Launch Quick Scan (~2 min)")
        self.quick_btn.setFixedHeight(44)
        self.quick_btn.clicked.connect(self.quick_scan_requested.emit)
        qc_layout.addWidget(self.quick_btn)

        cards_layout.addWidget(quick_card)

        # Full Test Card
        full_card = QFrame()
        full_card.setObjectName("cardFrame")
        fc_layout = QVBoxLayout(full_card)
        fc_layout.setContentsMargins(28, 28, 28, 28)
        fc_layout.setSpacing(16)

        fc_icon = QLabel("🔬")
        fc_icon.setStyleSheet("font-size: 36px;")
        fc_layout.addWidget(fc_icon)

        fc_title = QLabel("Full Verification Test")
        fc_title.setStyleSheet("font-size: 20px; font-weight: 700;")
        fc_layout.addWidget(fc_title)

        fc_desc = QLabel(
            "Deep diagnostic session with stress testing and interactive hardware checks (20-30 min).\n\n"
            "✓ Everything in Quick Scan\n"
            "✓ CPU & GPU thermal throttling stress tests\n"
            "✓ Fake-capacity drive write-verification\n"
            "✓ Memory bit-pattern integrity test (walking ones)\n"
            "✓ Battery 60s discharge rate stability test\n"
            "✓ Dead pixel, keyboard, and speaker diagnostics"
        )
        fc_desc.setStyleSheet("color: #94a3b8; line-height: 140%;")
        fc_layout.addWidget(fc_desc)

        fc_layout.addStretch()

        self.full_btn = QPushButton("Launch Full Test (~20 min)")
        self.full_btn.setObjectName("secondaryButton")
        self.full_btn.setFixedHeight(44)
        self.full_btn.clicked.connect(self.full_test_requested.emit)
        fc_layout.addWidget(self.full_btn)

        cards_layout.addWidget(full_card)

        main_layout.addLayout(cards_layout)

        # Bottom Bar: Seller Claims & Version
        bot_bar = QHBoxLayout()
        claims_btn = QPushButton("📋 Compare Against Seller Claims")
        claims_btn.setObjectName("secondaryButton")
        claims_btn.clicked.connect(self.seller_claims_requested.emit)
        bot_bar.addWidget(claims_btn)

        interactive_btn = QPushButton("🎮 Guided Diagnostics (Keyboard, Screen, Audio, Ports)")
        interactive_btn.setObjectName("secondaryButton")
        interactive_btn.clicked.connect(self.interactive_diagnostics_requested.emit)
        bot_bar.addWidget(interactive_btn)

        bot_bar.addStretch()

        ver_lbl = QLabel(f"HardwareVerify v{APP_VERSION} • Production Grade")
        ver_lbl.setObjectName("textMuted")
        bot_bar.addWidget(ver_lbl)

        main_layout.addLayout(bot_bar)
