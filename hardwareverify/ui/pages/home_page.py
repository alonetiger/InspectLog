"""Home landing page offering one-click Check PC and advanced diagnostics."""

from __future__ import annotations

import os

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QCursor, QFont, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hardwareverify.constants import APP_DISPLAY_NAME, APP_VERSION, LOGO_PATH
from hardwareverify.infra.admin import is_admin
from hardwareverify.ui.icons import GlassIcon, html_img, icon


class HomePage(QWidget):
    """Initial landing page featuring the one-click Check PC audit and diagnostics."""

    check_pc_requested = Signal()
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
        main_layout.setContentsMargins(40, 32, 40, 32)
        main_layout.setSpacing(24)

        # -------------------------------------------------------------
        # 1. Top Bar: Title, Admin Badge & Theme Toggle
        # -------------------------------------------------------------
        top_bar = QHBoxLayout()

        if os.path.exists(LOGO_PATH):
            logo_lbl = QLabel()
            pixmap = QPixmap(LOGO_PATH).scaledToHeight(46, Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(pixmap)
            top_bar.addWidget(logo_lbl)
            top_bar.addSpacing(14)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        title_lbl = QLabel(APP_DISPLAY_NAME)
        title_lbl.setObjectName("pageTitle")
        title_col.addWidget(title_lbl)

        sub_lbl = QLabel("Professional PC Hardware Authenticity, Health & Anti-Counterfeit Verification")
        sub_lbl.setObjectName("pageSubtitle")
        title_col.addWidget(sub_lbl)
        top_bar.addLayout(title_col)

        top_bar.addStretch()

        # Admin Badge
        admin_ok = is_admin()
        admin_badge = QLabel("🛡️ Administrator" if admin_ok else "⚠️ Standard User (Some checks limited)")
        admin_badge.setObjectName("badgeSuccess" if admin_ok else "badgeWarning")
        top_bar.addWidget(admin_badge)

        # Theme Toggle Button
        self.theme_btn = QPushButton("🌓 Theme")
        self.theme_btn.setObjectName("secondaryButton")
        self.theme_btn.setToolTip("Switch Glass Transparent theme between dark and light")
        self.theme_btn.clicked.connect(self.theme_toggled.emit)
        top_bar.addWidget(self.theme_btn)

        main_layout.addLayout(top_bar)

        # -------------------------------------------------------------
        # 2. Hero Card: Prominent "Check PC" Primary Action
        # -------------------------------------------------------------
        hero_card = QFrame()
        hero_card.setObjectName("heroCard")
        hero_layout = QVBoxLayout(hero_card)
        hero_layout.setContentsMargins(28, 24, 28, 24)
        hero_layout.setSpacing(16)

        hero_header = QHBoxLayout()
        hero_header.setSpacing(16)

        hero_header.addWidget(GlassIcon("computer", icon_size=44, padding=14), 0, Qt.AlignmentFlag.AlignTop)

        hero_text_col = QVBoxLayout()
        hero_text_col.setSpacing(4)
        hero_title = QLabel("One-Click Hardware Inspection & Health Audit")
        hero_title.setObjectName("heroTitle")
        hero_text_col.addWidget(hero_title)

        hero_desc = QLabel(
            "Safely inspects all components in real-time. Detects counterfeit/spoofed CPUs, reads battery wear %, "
            "drive SMART health & reallocated bad sectors, verified RAM speeds, GPU VRAM, and motherboard serial integrity."
        )
        hero_desc.setObjectName("textSecondary")
        hero_desc.setWordWrap(True)
        hero_text_col.addWidget(hero_desc)
        hero_header.addLayout(hero_text_col, 1)

        hero_layout.addLayout(hero_header)

        # Feature pills row
        pills_layout = QHBoxLayout()
        pills_layout.setSpacing(10)
        pills = [
            ("authenticity", "Anti-Spoofing Check"),
            ("battery", "Battery Wear %"),
            ("storage", "Drive SMART Health"),
            ("ram", "RAM Speed &amp; Channels"),
            ("cpu", "Genuine CPU Cores"),
            ("security", "Security &amp; Locks"),
        ]
        for icon_name, text in pills:
            pill = QLabel(f"{html_img(icon_name)}&nbsp; {text}")
            pill.setObjectName("pill")
            pills_layout.addWidget(pill)
        pills_layout.addStretch()
        hero_layout.addLayout(pills_layout)

        # Big "Check PC" Action Button
        action_row = QHBoxLayout()
        action_row.setSpacing(16)

        self.check_pc_btn = QPushButton("  Check PC")
        self.check_pc_btn.setIcon(icon("search"))
        self.check_pc_btn.setIconSize(QSize(26, 26))
        self.check_pc_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.check_pc_btn.setObjectName("heroButton")
        self.check_pc_btn.setFixedHeight(54)
        self.check_pc_btn.clicked.connect(self._on_check_pc_clicked)
        action_row.addWidget(self.check_pc_btn)

        eta_lbl = QLabel("⚡ Non-destructive read-only audit • Takes ~10-15 seconds • Displays in-app report")
        eta_lbl.setObjectName("textSecondary")
        action_row.addWidget(eta_lbl)
        action_row.addStretch()

        hero_layout.addLayout(action_row)
        main_layout.addWidget(hero_card)

        # -------------------------------------------------------------
        # 3. Secondary Diagnostics & Tools Cards
        # -------------------------------------------------------------
        sec_layout = QHBoxLayout()
        sec_layout.setSpacing(20)

        # Card A: Deep Stress Test
        stress_card = QFrame()
        stress_card.setObjectName("cardFrame")
        sc_layout = QVBoxLayout(stress_card)
        sc_layout.setContentsMargins(20, 18, 20, 18)
        sc_layout.setSpacing(10)

        sc_layout.addWidget(GlassIcon("stress", icon_size=30))

        sc_title = QLabel("Deep Stress Test")
        sc_title.setObjectName("cardTitle")
        sc_layout.addWidget(sc_title)

        sc_desc = QLabel(
            "Extended diagnostic with CPU & GPU thermal throttling stress tests, "
            "RAM walking-ones bit integrity test, and fake-capacity drive verification (15-20 min)."
        )
        sc_desc.setObjectName("cardBody")
        sc_desc.setWordWrap(True)
        sc_layout.addWidget(sc_desc)
        sc_layout.addStretch()

        self.full_btn = QPushButton("Launch Stress Test (~20 min)")
        self.full_btn.setObjectName("secondaryButton")
        self.full_btn.setFixedHeight(38)
        self.full_btn.clicked.connect(self.full_test_requested.emit)
        sc_layout.addWidget(self.full_btn)
        sec_layout.addWidget(stress_card)

        # Card B: Compare Seller Claims
        claims_card = QFrame()
        claims_card.setObjectName("cardFrame")
        cc_layout = QVBoxLayout(claims_card)
        cc_layout.setContentsMargins(20, 18, 20, 18)
        cc_layout.setSpacing(10)

        cc_layout.addWidget(GlassIcon("claims", icon_size=30))

        cc_title = QLabel("Seller Claims Verification")
        cc_title.setObjectName("cardTitle")
        cc_layout.addWidget(cc_title)

        cc_desc = QLabel(
            "Enter what the seller advertised (CPU, RAM, SSD size, battery health). "
            "The app will cross-check and highlight any mismatches or downgrades."
        )
        cc_desc.setObjectName("cardBody")
        cc_desc.setWordWrap(True)
        cc_layout.addWidget(cc_desc)
        cc_layout.addStretch()

        self.claims_btn = QPushButton("Enter Advertised Claims")
        self.claims_btn.setObjectName("secondaryButton")
        self.claims_btn.setFixedHeight(38)
        self.claims_btn.clicked.connect(self.seller_claims_requested.emit)
        cc_layout.addWidget(self.claims_btn)
        sec_layout.addWidget(claims_card)

        # Card C: Interactive Guided Diagnostics
        guide_card = QFrame()
        guide_card.setObjectName("cardFrame")
        gc_layout = QVBoxLayout(guide_card)
        gc_layout.setContentsMargins(20, 18, 20, 18)
        gc_layout.setSpacing(10)

        gc_layout.addWidget(GlassIcon("diagnostics", icon_size=30))

        gc_title = QLabel("Hardware Diagnostics")
        gc_title.setObjectName("cardTitle")
        gc_layout.addWidget(gc_title)

        gc_desc = QLabel(
            "Interactive physical tests for screen dead pixels, keyboard key map, "
            "touchpad, webcam video preview, mic VU meter, stereo speaker tones & USB ports."
        )
        gc_desc.setObjectName("cardBody")
        gc_desc.setWordWrap(True)
        gc_layout.addWidget(gc_desc)
        gc_layout.addStretch()

        self.interactive_btn = QPushButton("Guided Peripherals Test")
        self.interactive_btn.setObjectName("secondaryButton")
        self.interactive_btn.setFixedHeight(38)
        self.interactive_btn.clicked.connect(self.interactive_diagnostics_requested.emit)
        gc_layout.addWidget(self.interactive_btn)
        sec_layout.addWidget(guide_card)

        main_layout.addLayout(sec_layout)

        # -------------------------------------------------------------
        # 4. Bottom Footer: Version & Status
        # -------------------------------------------------------------
        main_layout.addStretch()

        bot_bar = QHBoxLayout()
        status_lbl = QLabel(f"Inspect Log v{APP_VERSION} • Production Grade • Dedicated In-App Hardware Auditor • Icons by srip from Flaticon")
        status_lbl.setObjectName("textMuted")
        bot_bar.addWidget(status_lbl)
        bot_bar.addStretch()
        main_layout.addLayout(bot_bar)

        # Keep quick_btn reference for backward-compatibility with tests
        self.quick_btn = self.check_pc_btn

    def _on_check_pc_clicked(self) -> None:
        """Handle the primary Check PC button click."""
        self.check_pc_requested.emit()
        self.quick_scan_requested.emit()
