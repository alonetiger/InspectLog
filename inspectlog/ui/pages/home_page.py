"""Home landing page offering one-click Check PC and advanced diagnostics."""

from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
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

from inspectlog.constants import APP_DISPLAY_NAME, APP_VERSION, LOGO_PATH
from inspectlog.infra.admin import is_admin


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
        title_lbl.setStyleSheet("font-size: 26px; font-weight: 800; color: #F8FAFC;")
        title_col.addWidget(title_lbl)

        sub_lbl = QLabel("Professional PC Hardware Authenticity, Health & Anti-Counterfeit Verification")
        sub_lbl.setObjectName("pageSubtitle")
        sub_lbl.setStyleSheet("color: #94A3B8; font-size: 13px;")
        title_col.addWidget(sub_lbl)
        top_bar.addLayout(title_col)

        top_bar.addStretch()

        # Admin Badge
        admin_ok = is_admin()
        admin_badge = QLabel("🛡️ Administrator" if admin_ok else "⚠️ Standard User (Some checks limited)")
        admin_badge.setStyleSheet(
            "background-color: #064E3B; color: #34D399; padding: 6px 14px; border-radius: 8px; font-weight: 600; font-size: 12px;"
            if admin_ok
            else "background-color: #78350F; color: #FBBF24; padding: 6px 14px; border-radius: 8px; font-weight: 600; font-size: 12px;"
        )
        top_bar.addWidget(admin_badge)

        # Theme Toggle Button
        self.theme_btn = QPushButton("🌙 / ☀️")
        self.theme_btn.setObjectName("secondaryButton")
        self.theme_btn.setToolTip("Toggle Dark / Light Theme")
        self.theme_btn.setFixedWidth(68)
        self.theme_btn.clicked.connect(self.theme_toggled.emit)
        top_bar.addWidget(self.theme_btn)

        main_layout.addLayout(top_bar)

        # -------------------------------------------------------------
        # 2. Hero Card: Prominent "Check PC" Primary Action
        # -------------------------------------------------------------
        hero_card = QFrame()
        hero_card.setObjectName("cardFrame")
        hero_card.setStyleSheet("""
            QFrame#cardFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1E293B, stop:1 #0F172A);
                border: 2px solid #38BDF8;
                border-radius: 14px;
                padding: 24px;
            }
        """)
        hero_layout = QVBoxLayout(hero_card)
        hero_layout.setContentsMargins(28, 24, 28, 24)
        hero_layout.setSpacing(16)

        hero_header = QHBoxLayout()
        hero_header.setSpacing(16)

        hero_icon = QLabel("💻")
        hero_icon.setStyleSheet("font-size: 42px;")
        hero_header.addWidget(hero_icon)

        hero_text_col = QVBoxLayout()
        hero_text_col.setSpacing(4)
        hero_title = QLabel("One-Click Hardware Inspection & Health Audit")
        hero_title.setStyleSheet("font-size: 22px; font-weight: 800; color: #FFFFFF;")
        hero_text_col.addWidget(hero_title)

        hero_desc = QLabel(
            "Safely inspects all components in real-time. Detects counterfeit/spoofed CPUs, reads battery wear %,\n"
            "drive SMART health & reallocated bad sectors, verified RAM speeds, GPU VRAM, and motherboard serial integrity."
        )
        hero_desc.setStyleSheet("color: #CBD5E1; font-size: 13px; line-height: 140%;")
        hero_text_col.addWidget(hero_desc)
        hero_header.addLayout(hero_text_col, 1)

        hero_layout.addLayout(hero_header)

        # Feature pills row
        pills_layout = QHBoxLayout()
        pills_layout.setSpacing(10)
        pills = [
            "🛡️ Anti-Spoofing Check",
            "🔋 Battery Wear %",
            "💾 Drive SMART Health",
            "🧠 RAM Speed & Channels",
            "⚡ Genuine CPU Cores",
            "🔒 Security & Locks",
        ]
        for p in pills:
            pill = QLabel(p)
            pill.setStyleSheet(
                "background-color: rgba(56, 189, 248, 0.12); color: #38BDF8; "
                "padding: 5px 12px; border-radius: 6px; font-size: 11px; font-weight: 600;"
            )
            pills_layout.addWidget(pill)
        pills_layout.addStretch()
        hero_layout.addLayout(pills_layout)

        # Big "Check PC" Action Button
        action_row = QHBoxLayout()
        action_row.setSpacing(16)

        self.check_pc_btn = QPushButton("🔍 Check PC")
        self.check_pc_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.check_pc_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:1 #2563EB);
                color: #FFFFFF;
                font-size: 18px;
                font-weight: 800;
                border-radius: 10px;
                padding: 14px 40px;
                border: 1px solid #60A5FA;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369A1, stop:1 #1D4ED8);
                border: 1px solid #93C5FD;
            }
            QPushButton:pressed {
                background: #1E40AF;
            }
        """)
        self.check_pc_btn.setFixedHeight(54)
        self.check_pc_btn.clicked.connect(self._on_check_pc_clicked)
        action_row.addWidget(self.check_pc_btn)

        eta_lbl = QLabel("⚡ Non-destructive read-only audit • Takes ~10-15 seconds • Displays in-app report")
        eta_lbl.setStyleSheet("color: #94A3B8; font-size: 13px; font-style: italic;")
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

        sc_icon = QLabel("🔬")
        sc_icon.setStyleSheet("font-size: 28px;")
        sc_layout.addWidget(sc_icon)

        sc_title = QLabel("Deep Stress Test")
        sc_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #F8FAFC;")
        sc_layout.addWidget(sc_title)

        sc_desc = QLabel(
            "Extended diagnostic with CPU & GPU thermal throttling stress tests, "
            "RAM walking-ones bit integrity test, and fake-capacity drive verification (15-20 min)."
        )
        sc_desc.setStyleSheet("color: #94A3B8; font-size: 12px; line-height: 135%;")
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

        cc_icon = QLabel("📋")
        cc_icon.setStyleSheet("font-size: 28px;")
        cc_layout.addWidget(cc_icon)

        cc_title = QLabel("Seller Claims Verification")
        cc_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #F8FAFC;")
        cc_layout.addWidget(cc_title)

        cc_desc = QLabel(
            "Enter what the seller advertised (CPU, RAM, SSD size, battery health). "
            "The app will cross-check and highlight any mismatches or downgrades."
        )
        cc_desc.setStyleSheet("color: #94A3B8; font-size: 12px; line-height: 135%;")
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

        gc_icon = QLabel("🎮")
        gc_icon.setStyleSheet("font-size: 28px;")
        gc_layout.addWidget(gc_icon)

        gc_title = QLabel("Hardware Diagnostics")
        gc_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #F8FAFC;")
        gc_layout.addWidget(gc_title)

        gc_desc = QLabel(
            "Interactive physical tests for screen dead pixels, keyboard key map, "
            "touchpad, webcam video preview, mic VU meter, stereo speaker tones & USB ports."
        )
        gc_desc.setStyleSheet("color: #94A3B8; font-size: 12px; line-height: 135%;")
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
        status_lbl = QLabel(f"Inspect Log v{APP_VERSION} • Production Grade • Dedicated In-App Hardware Auditor")
        status_lbl.setObjectName("textMuted")
        status_lbl.setStyleSheet("color: #64748B; font-size: 12px;")
        bot_bar.addWidget(status_lbl)
        bot_bar.addStretch()
        main_layout.addLayout(bot_bar)

        # Keep quick_btn reference for backward-compatibility with tests
        self.quick_btn = self.check_pc_btn

    def _on_check_pc_clicked(self) -> None:
        """Handle the primary Check PC button click."""
        self.check_pc_requested.emit()
        self.quick_scan_requested.emit()
