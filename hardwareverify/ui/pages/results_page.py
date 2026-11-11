"""Dedicated In-App Hardware Inspection Report dashboard displaying detailed telemetry."""

from __future__ import annotations

import time
from typing import Any

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from hardwareverify.core.models import ModuleResult, Status
from hardwareverify.infra.config import SellerClaims
from hardwareverify.report.claims_matcher import ClaimsMatcher, ClaimsReport
from hardwareverify.report.scoring import ScoringEngine, ScoringSummary
from hardwareverify.ui.widgets.health_gauge import HealthGauge
from hardwareverify.ui.icons import html_img, icon
from hardwareverify.ui.theme import ThemeManager
from hardwareverify.ui.widgets.module_card import ModuleCard


class ResultsPage(QWidget):
    """Dedicated post-scan in-app hardware report dashboard."""

    check_pc_again_requested = Signal()
    new_scan_requested = Signal()
    export_pdf_requested = Signal()
    export_json_requested = Signal()
    guided_diagnostics_requested = Signal()
    claims_edit_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._results: list[ModuleResult] = []
        self._claims: SellerClaims | None = None
        self._scoring_engine = ScoringEngine()
        self._claims_matcher = ClaimsMatcher()
        self._module_cards: list[tuple[str, ModuleCard]] = []
        self._active_category = "all"

        self._setup_ui()

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(28, 20, 28, 20)
        root_layout.setSpacing(14)

        # -------------------------------------------------------------
        # 1. Top Navigation & Action Header
        # -------------------------------------------------------------
        top_header = QHBoxLayout()

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        page_title = QLabel("Hardware Inspection Report")
        page_title.setObjectName("pageTitle")
        title_col.addWidget(page_title)

        self.report_meta_lbl = QLabel("Inspection completed • All telemetry verified in software")
        self.report_meta_lbl.setObjectName("textSecondary")
        title_col.addWidget(self.report_meta_lbl)
        top_header.addLayout(title_col, 1)

        # In-App Action Buttons
        actions_row = QHBoxLayout()
        actions_row.setSpacing(10)

        self.recheck_btn = QPushButton(" Check PC Again")
        self.recheck_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.recheck_btn.setFixedHeight(36)
        self.recheck_btn.setMinimumWidth(160)
        self.recheck_btn.clicked.connect(self._on_check_again)
        actions_row.addWidget(self.recheck_btn)

        self.home_btn = QPushButton(" Home")
        self.home_btn.setObjectName("secondaryButton")
        self.home_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.home_btn.setFixedHeight(36)
        self.home_btn.clicked.connect(self.new_scan_requested.emit)
        actions_row.addWidget(self.home_btn)

        self.guided_btn = QPushButton(" Diagnostics")
        self.guided_btn.setObjectName("secondaryButton")
        self.guided_btn.setToolTip("Interactive test for Screen, Keyboard, Audio & Ports")
        self.guided_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.guided_btn.setFixedHeight(36)
        self.guided_btn.clicked.connect(self.guided_diagnostics_requested.emit)
        actions_row.addWidget(self.guided_btn)

        self.claims_btn = QPushButton(" Seller Claims")
        self.claims_btn.setObjectName("secondaryButton")
        self.claims_btn.setToolTip("Compare results with seller advertised specs")
        self.claims_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.claims_btn.setFixedHeight(36)
        self.claims_btn.clicked.connect(self.claims_edit_requested.emit)
        actions_row.addWidget(self.claims_btn)

        for btn, icon_name in (
            (self.recheck_btn, "search"),
            (self.home_btn, "computer"),
            (self.guided_btn, "diagnostics"),
            (self.claims_btn, "claims"),
        ):
            btn.setIcon(icon(icon_name))
            btn.setIconSize(QSize(18, 18))

        # Optional Export Dropdown (demoted to secondary utility)
        self.export_btn = QPushButton("Export File ▼")
        self.export_btn.setObjectName("secondaryButton")
        self.export_btn.setFixedHeight(36)
        self.export_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.export_menu = QMenu(self)
        self.export_menu.addAction("Export PDF Report", self.export_pdf_requested.emit)
        self.export_menu.addAction("Export JSON Audit Data", self.export_json_requested.emit)
        self.export_btn.setMenu(self.export_menu)
        actions_row.addWidget(self.export_btn)

        top_header.addLayout(actions_row)
        root_layout.addLayout(top_header)

        # -------------------------------------------------------------
        # 2. Main Scroll Area for In-App Report Contents
        # -------------------------------------------------------------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("reportScrollArea")
        # Content reflows to the window width instead of scrolling sideways
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        root_layout.addWidget(scroll)

        self.content_widget = QWidget()
        scroll.setWidget(self.content_widget)

        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 4, 4, 16)
        self.content_layout.setSpacing(16)

        # -------------------------------------------------------------
        # 3. Executive Summary Card (Health Gauge + Vitals Strip)
        # -------------------------------------------------------------
        self.summary_card = QFrame()
        self.summary_card.setObjectName("heroCard")
        summary_layout = QVBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(18, 16, 18, 16)
        summary_layout.setSpacing(16)

        # Row 1: Gauge + Verdict Title + System Identity Banner
        top_summary_row = QHBoxLayout()
        top_summary_row.setSpacing(20)

        self.overall_gauge = HealthGauge(score=100, status=Status.PASS, size=115)
        top_summary_row.addWidget(self.overall_gauge)

        verdict_col = QVBoxLayout()
        verdict_col.setSpacing(6)

        self.verdict_title = QLabel("Hardware Verification Summary")
        self.verdict_title.setObjectName("heroTitle")
        self.verdict_title.setWordWrap(True)
        verdict_col.addWidget(self.verdict_title)

        self.verdict_subtitle = QLabel("All scanned components evaluated.")
        self.verdict_subtitle.setObjectName("textSecondary")
        self.verdict_subtitle.setWordWrap(True)
        verdict_col.addWidget(self.verdict_subtitle)

        # Device Identity Pill Banner
        self.device_identity_banner = QLabel("System: Scanning...")
        self.device_identity_banner.setObjectName("identityPill")
        verdict_col.addWidget(self.device_identity_banner, 0, Qt.AlignmentFlag.AlignLeft)
        top_summary_row.addLayout(verdict_col, 1)

        summary_layout.addLayout(top_summary_row)

        # Row 2: Vitals Ribbon (4 quick-stat badges)
        self.vitals_layout = QHBoxLayout()
        self.vitals_layout.setSpacing(12)

        self.vital_authenticity = self._create_vital_badge("authenticity", "Authenticity", "Verified Genuine", "success")
        self.vital_battery = self._create_vital_badge("battery", "Battery Health", "Evaluating...", "info")
        self.vital_storage = self._create_vital_badge("storage", "Storage SMART", "Evaluating...", "info")
        self.vital_cpu = self._create_vital_badge("cpu", "Processor", "Evaluating...", "info")

        self.vitals_layout.addWidget(self.vital_authenticity)
        self.vitals_layout.addWidget(self.vital_battery)
        self.vitals_layout.addWidget(self.vital_storage)
        self.vitals_layout.addWidget(self.vital_cpu)

        summary_layout.addLayout(self.vitals_layout)
        self.content_layout.addWidget(self.summary_card)

        # -------------------------------------------------------------
        # 4. Red Flags & Actionable Buyer Recommendations Container
        # -------------------------------------------------------------
        self.red_flags_container = QVBoxLayout()
        self.red_flags_container.setSpacing(8)
        self.content_layout.addLayout(self.red_flags_container)

        # -------------------------------------------------------------
        # 5. Seller Claims Container
        # -------------------------------------------------------------
        self.claims_container = QVBoxLayout()
        self.claims_container.setSpacing(8)
        self.content_layout.addLayout(self.claims_container)

        # -------------------------------------------------------------
        # 6. Category Filter Bar (Tabs)
        # -------------------------------------------------------------
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)

        filter_lbl = QLabel("Category:")
        filter_lbl.setObjectName("textSecondary")
        filter_bar.addWidget(filter_lbl)

        self.filter_group = QButtonGroup(self)
        self.filter_group.setExclusive(True)

        categories = [
            ("all", "All Components", ""),
            ("processor_memory", "CPU & RAM", "cpu"),
            ("storage", "Storage", "storage"),
            ("battery", "Battery", "battery"),
            ("graphics_display", "Graphics & Display", "gpu"),
            ("system_security", "Security & Identity", "security"),
            ("thermals_io", "Thermals & I/O", "thermals"),
        ]
        # QPushButton treats a single "&" as a shortcut marker and hides it
        categories = [(cat_id, (" " if icon_name else "") + title.replace("&", "&&"), icon_name) for cat_id, title, icon_name in categories]

        for idx, (cat_id, cat_title, icon_name) in enumerate(categories):
            btn = QPushButton(cat_title)
            btn.setCheckable(True)
            btn.setChecked(idx == 0)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setObjectName("filterChip")
            if icon_name:
                btn.setIcon(icon(icon_name))
                btn.setIconSize(QSize(16, 16))
            btn.clicked.connect(lambda checked=False, cid=cat_id: self._filter_category(cid))
            self.filter_group.addButton(btn, idx)
            filter_bar.addWidget(btn)

        filter_bar.addStretch()
        self.content_layout.addLayout(filter_bar)

        # -------------------------------------------------------------
        # 7. Module Cards Grid
        # -------------------------------------------------------------
        self.grid_container = QWidget()
        self.cards_grid = QGridLayout(self.grid_container)
        self.cards_grid.setContentsMargins(0, 0, 0, 0)
        self.cards_grid.setHorizontalSpacing(16)
        self.cards_grid.setVerticalSpacing(16)
        self.content_layout.addWidget(self.grid_container)

        # Backward compatibility aliases for existing tests
        self.pdf_btn = self.export_btn
        self.json_btn = self.export_btn
        self.interactive_btn = self.guided_btn
        self.new_scan_btn = self.home_btn

    def _create_vital_badge(self, icon_name: str, title: str, default_val: str, tone: str) -> QFrame:
        """Create a compact quick-stat telemetry badge for the header ribbon."""
        box = QFrame()
        box.setObjectName("vitalBadge")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(3)

        lbl_title = QLabel(f"{html_img(icon_name, 13)}&nbsp; {title.upper()}")
        lbl_title.setObjectName("vitalTitle")
        layout.addWidget(lbl_title)

        lbl_val = QLabel(default_val)
        lbl_val.setWordWrap(True)
        layout.addWidget(lbl_val)

        box.value_label = lbl_val  # type: ignore[attr-defined]
        self._set_vital(box, default_val, tone)
        return box

    @staticmethod
    def _set_vital(box: QFrame, text: str, tone: str) -> None:
        """Set a vital badge's value; tone is success, warning, danger, info or muted."""
        label: QLabel = box.value_label  # type: ignore[attr-defined]
        label.setText(text)
        label.setObjectName("textSecondary" if tone == "muted" else f"{tone}Text")
        label.setStyleSheet("font-size: 13px; font-weight: 700;")
        # objectName selectors are only re-evaluated on polish
        label.style().unpolish(label)
        label.style().polish(label)

    def display_results(
        self,
        results: list[ModuleResult],
        claims: SellerClaims | None = None,
    ) -> None:
        """Render results from all tested modules with scoring and in-app breakdown."""
        self._results = results
        if claims is not None:
            self._claims = claims

        # Evaluate using centralized ScoringEngine
        summary = self._scoring_engine.evaluate(results)

        if summary.verdict == "HIGH":
            gauge_status = Status.PASS
        elif summary.verdict == "MODERATE":
            gauge_status = Status.WARNING
        else:
            gauge_status = Status.FAIL

        self.overall_gauge.set_score(summary.overall_score, gauge_status)
        self.verdict_title.setText(summary.verdict_title)
        self.verdict_subtitle.setText(summary.verdict_explanation)

        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
        self.report_meta_lbl.setText(f"Inspection completed on {timestamp_str} • All readings verified in software")

        # 1. Update System Identity Banner & Vitals Ribbon
        self._update_system_vitals(results)

        # 2. Render Seller Claims Table (if claims entered)
        self._render_seller_claims()

        # 3. Render Red Flags & Actionable Buyer Recommendations
        self._render_red_flags(summary)

        # 4. Populate module cards in grid
        self._populate_module_cards(results)

    def _update_system_vitals(self, results: list[ModuleResult]) -> None:
        """Extract high-level vitals to populate header ribbon."""
        sys_res = next((r for r in results if r.module_name == "system_identity"), None)
        cpu_res = next((r for r in results if r.module_name == "cpu"), None)
        bat_res = next((r for r in results if r.module_name == "battery"), None)
        storage_res = [r for r in results if r.module_name.startswith("storage")]

        # System Banner
        if sys_res:
            mfg = sys_res.readings.get("manufacturer")
            model = sys_res.readings.get("model")
            serial = sys_res.readings.get("serial_number")
            mfg_str = mfg.value if mfg and mfg.is_available else "Generic PC"
            model_str = model.value if model and model.is_available else "System"
            serial_str = serial.value if serial and serial.is_available else "Unknown"
            self.device_identity_banner.setText(f"System: {mfg_str} {model_str}  |  Serial: {serial_str}")

        # Authenticity Vital
        if any(r.module_name == "cpu" and any("spoofed" in e.lower() for e in r.errors) for r in results):
            self._set_vital(self.vital_authenticity, "❌ SPOOFED CPU DETECTED", "danger")
        elif sys_res and any("serial" in w.lower() for w in sys_res.warnings):
            self._set_vital(self.vital_authenticity, "⚠️ Generic Serial", "warning")
        else:
            self._set_vital(self.vital_authenticity, "✅ Verified Genuine", "success")

        # Battery Vital
        if bat_res:
            if not bat_res.is_applicable:
                self._set_vital(self.vital_battery, "🔌 Desktop (AC Power)", "muted")
            else:
                wear = bat_res.readings.get("wear_percentage")
                wear_val = f"{wear.value}% Wear" if wear and wear.is_available else "Available"
                if wear and wear.is_available and float(wear.value) > 40:
                    self._set_vital(self.vital_battery, f"⚠️ {wear_val} (Replace)", "danger")
                elif wear and wear.is_available and float(wear.value) > 25:
                    self._set_vital(self.vital_battery, f"⚠️ {wear_val} (Fair)", "warning")
                else:
                    self._set_vital(self.vital_battery, f"✅ {wear_val} (Good)", "success")

        # Storage Vital
        if storage_res:
            all_smart_pass = all(
                r.readings.get("smart_health") and r.readings["smart_health"].value == "Passed"
                for r in storage_res
            )
            drive_count = len(storage_res)
            if all_smart_pass:
                self._set_vital(
                    self.vital_storage,
                    f"✅ 100% SMART OK ({drive_count} drive{'s' if drive_count > 1 else ''})",
                    "success",
                )
            else:
                self._set_vital(self.vital_storage, "❌ SMART Warning / Failing", "danger")

        # CPU Vital
        if cpu_res:
            model = cpu_res.readings.get("cpu_model")
            cores = cpu_res.readings.get("physical_cores")
            threads = cpu_res.readings.get("logical_processors")
            model_str = model.value if model and model.is_available else "Processor"
            c_str = f" ({cores.value}C/{threads.value}T)" if cores and threads and cores.is_available and threads.is_available else ""
            self._set_vital(self.vital_cpu, f"{model_str}{c_str}", "info")

    def _render_seller_claims(self) -> None:
        """Render the comparison table between claimed and detected hardware."""
        while self.claims_container.count():
            item = self.claims_container.takeAt(0)
            if item.widget():
                item.widget().hide()  # deleteLater is deferred; hidden so it never paints under the new content
                item.widget().deleteLater()

        if not self._claims or not self._claims.has_claims:
            return

        report = self._claims_matcher.compare(self._claims, self._results)
        card = QFrame()
        card.setObjectName("cardFrame")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel(f"{html_img('claims', 18)}&nbsp; Seller Advertised Claims Match Report ({report.matches_count}/{len(report.items)} Matched)")
        title.setObjectName("cardTitle")
        header.addWidget(title)
        header.addStretch()

        badge_txt = "✓ ALL ADVERTISED SPECS MATCH" if report.all_matched else f"⚠ {report.mismatches_count} SPEC MISMATCH(ES)"
        badge = QLabel(badge_txt)
        badge.setObjectName("badgeSuccess" if report.all_matched else "badgeDanger")
        header.addWidget(badge)
        layout.addLayout(header)

        # Table of claim comparisons
        table = QTableWidget(len(report.items), 4)
        table.setHorizontalHeaderLabels(["Component", "Advertised Spec", "Detected Hardware", "Match Verdict"])
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)

        colors = ThemeManager.get_colors()
        for row, it in enumerate(report.items):
            table.setItem(row, 0, QTableWidgetItem(it.component))
            table.setItem(row, 1, QTableWidgetItem(it.claimed_value))
            actual_item = QTableWidgetItem(f"{it.actual_value} — {it.details}")
            table.setItem(row, 2, actual_item)

            v_item = QTableWidgetItem("✓ Match" if it.is_match else "✕ Mismatch")
            v_item.setForeground(QColor(colors["accent_success"] if it.is_match else colors["accent_danger"]))
            table.setItem(row, 3, v_item)

        table.setFixedHeight(min(220, 36 + len(report.items) * 32))
        layout.addWidget(table)
        self.claims_container.addWidget(card)

    def _render_red_flags(self, summary: ScoringSummary) -> None:
        """Render high-priority buyer issues and actionable tips."""
        while self.red_flags_container.count():
            item = self.red_flags_container.takeAt(0)
            if item.widget():
                item.widget().hide()  # deleteLater is deferred; hidden so it never paints under the new content
                item.widget().deleteLater()

        if not summary.red_flags and not summary.recommendations:
            clean_box = QFrame()
            clean_box.setObjectName("successCard")
            clayout = QHBoxLayout(clean_box)
            clayout.setContentsMargins(16, 12, 16, 12)
            cl_icon = QLabel("✅")
            cl_icon.setStyleSheet("font-size: 20px;")
            clayout.addWidget(cl_icon)
            cl_txt = QLabel("<b>Clean Hardware Health:</b> No counterfeit components, failing SMART sectors, or severe wear detected.")
            cl_txt.setObjectName("successText")
            clayout.addWidget(cl_txt)
            clayout.addStretch()
            self.red_flags_container.addWidget(clean_box)
            return

        has_fail = summary.verdict == "LOW"
        rf_box = QFrame()
        rf_box.setObjectName("dangerCard" if has_fail else "warningCard")

        rf_box_layout = QVBoxLayout(rf_box)
        rf_box_layout.setContentsMargins(16, 14, 16, 14)
        rf_box_layout.setSpacing(8)

        rf_title = QLabel("🚩 Potential Issues & Actionable Buyer Notes:")
        rf_title.setObjectName("dangerText" if has_fail else "warningText")
        rf_title.setStyleSheet("font-size: 15px; font-weight: 700;")
        rf_box_layout.addWidget(rf_title)

        for flag in summary.red_flags:
            lbl = QLabel(f"• <b>Issue:</b> {flag}")
            lbl.setWordWrap(True)
            rf_box_layout.addWidget(lbl)

        for rec in summary.recommendations:
            lbl = QLabel(f"• <b>Buyer Tip:</b> {rec}")
            lbl.setWordWrap(True)
            lbl.setObjectName("infoText")
            rf_box_layout.addWidget(lbl)

        self.red_flags_container.addWidget(rf_box)

    def _populate_module_cards(self, results: list[ModuleResult]) -> None:
        """Create and lay out module cards."""
        # Clear existing
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            if item.widget():
                item.widget().hide()  # deleteLater is deferred; hidden so it never paints under the new content
                item.widget().deleteLater()

        self._module_cards.clear()

        for mod_res in results:
            card = ModuleCard(mod_res)
            category = self._classify_category(mod_res.module_name)
            self._module_cards.append((category, card))

        self._relayout_cards()

    def _classify_category(self, module_name: str) -> str:
        """Map module name to category filter ID."""
        if module_name in ("cpu", "ram"):
            return "processor_memory"
        elif module_name.startswith("storage"):
            return "storage"
        elif module_name == "battery":
            return "battery"
        elif module_name.startswith("gpu") or module_name.startswith("display"):
            return "graphics_display"
        elif module_name in ("system_identity", "security"):
            return "system_security"
        else:
            return "thermals_io"

    def _filter_category(self, category_id: str) -> None:
        """Filter visible cards based on the selected category tab."""
        self._active_category = category_id
        self._relayout_cards()

    def _relayout_cards(self) -> None:
        """Place matching cards into the 2-column grid."""
        # Remove from grid
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        filtered = [
            card for cat, card in self._module_cards
            if self._active_category == "all" or cat == self._active_category
        ]

        col_count = 2
        for idx, card in enumerate(filtered):
            card.show()
            row = idx // col_count
            col = idx % col_count
            self.cards_grid.addWidget(card, row, col)

    def _on_check_again(self) -> None:
        """Start a fresh scan. Emitting new_scan_requested here too would send the
        window back to the Home page while the new scan runs in the background."""
        self.check_pc_again_requested.emit()
