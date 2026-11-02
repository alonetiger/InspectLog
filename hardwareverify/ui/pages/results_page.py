"""Results page displaying summary verdict, red flags, claims matcher, and module cards."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
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
from hardwareverify.ui.widgets.module_card import ModuleCard


class ResultsPage(QWidget):
    """Post-scan analysis dashboard showing overall grade, red flags, and cards."""

    export_pdf_requested = Signal()
    export_json_requested = Signal()
    new_scan_requested = Signal()
    guided_diagnostics_requested = Signal()
    claims_edit_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._results: list[ModuleResult] = []
        self._claims: SellerClaims | None = None
        self._scoring_engine = ScoringEngine()
        self._claims_matcher = ClaimsMatcher()
        self._setup_ui()

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(30, 24, 30, 24)
        root_layout.setSpacing(16)

        # Scroll area to comfortably handle arbitrary number of module cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        root_layout.addWidget(scroll)

        self.content_widget = QWidget()
        scroll.setWidget(self.content_widget)

        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.setSpacing(18)

        # Summary Header Card
        self.summary_card = QFrame()
        self.summary_card.setObjectName("cardFrame")
        summary_layout = QHBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(24, 20, 24, 20)
        summary_layout.setSpacing(24)

        # Overall Health Gauge
        self.overall_gauge = HealthGauge(score=100, status=Status.PASS, size=115)
        summary_layout.addWidget(self.overall_gauge)

        # Summary text
        summary_col = QVBoxLayout()
        summary_col.setSpacing(6)
        self.verdict_title = QLabel("Hardware Verification Summary")
        self.verdict_title.setStyleSheet("font-size: 20px; font-weight: 700;")
        summary_col.addWidget(self.verdict_title)

        self.verdict_subtitle = QLabel("All scanned components evaluated.")
        self.verdict_subtitle.setObjectName("textSecondary")
        self.verdict_subtitle.setWordWrap(True)
        summary_col.addWidget(self.verdict_subtitle)

        summary_layout.addLayout(summary_col, 1)

        # Action Buttons in Header
        actions_col = QVBoxLayout()
        actions_col.setSpacing(8)

        self.interactive_btn = QPushButton("🎮 Guided Diagnostics")
        self.interactive_btn.clicked.connect(self.guided_diagnostics_requested.emit)
        actions_col.addWidget(self.interactive_btn)

        self.claims_btn = QPushButton("📋 Seller Claims")
        self.claims_btn.setObjectName("secondaryButton")
        self.claims_btn.clicked.connect(self.claims_edit_requested.emit)
        actions_col.addWidget(self.claims_btn)

        self.pdf_btn = QPushButton("📄 Export PDF Report")
        self.pdf_btn.setObjectName("secondaryButton")
        self.pdf_btn.clicked.connect(self.export_pdf_requested.emit)
        actions_col.addWidget(self.pdf_btn)

        self.json_btn = QPushButton("💾 Export JSON Data")
        self.json_btn.setObjectName("secondaryButton")
        self.json_btn.clicked.connect(self.export_json_requested.emit)
        actions_col.addWidget(self.json_btn)

        self.new_scan_btn = QPushButton("🔄 New Scan")
        self.new_scan_btn.setObjectName("secondaryButton")
        self.new_scan_btn.clicked.connect(self.new_scan_requested.emit)
        actions_col.addWidget(self.new_scan_btn)

        summary_layout.addLayout(actions_col)
        self.content_layout.addWidget(self.summary_card)

        # Seller Claims Comparison Container
        self.claims_container = QVBoxLayout()
        self.content_layout.addLayout(self.claims_container)

        # Red Flags / Warnings Container
        self.red_flags_container = QVBoxLayout()
        self.content_layout.addLayout(self.red_flags_container)

        # Module Cards Grid
        self.grid_container = QWidget()
        self.cards_grid = QGridLayout(self.grid_container)
        self.cards_grid.setContentsMargins(0, 0, 0, 0)
        self.cards_grid.setHorizontalSpacing(18)
        self.cards_grid.setVerticalSpacing(18)
        self.content_layout.addWidget(self.grid_container)

    def display_results(
        self,
        results: list[ModuleResult],
        claims: SellerClaims | None = None,
    ) -> None:
        """Render results from all tested modules with scoring engine and claims matcher."""
        self._results = results
        if claims is not None:
            self._claims = claims

        # Evaluate using centralized ScoringEngine
        summary = self._scoring_engine.evaluate(results)

        # Map verdict to Status enum for the gauge
        if summary.verdict == "HIGH":
            gauge_status = Status.PASS
        elif summary.verdict == "MODERATE":
            gauge_status = Status.WARNING
        else:
            gauge_status = Status.FAIL

        self.overall_gauge.set_score(summary.overall_score, gauge_status)
        self.verdict_title.setText(summary.verdict_title)
        self.verdict_subtitle.setText(summary.verdict_explanation)

        # 1. Render Seller Claims Table (if claims entered)
        self._render_seller_claims()

        # 2. Render Red Flags & Recommendations
        self._render_red_flags(summary)

        # 3. Populate cards in a 2-column grid
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        col_count = 2
        for idx, mod_res in enumerate(results):
            card = ModuleCard(mod_res)
            row = idx // col_count
            col = idx % col_count
            self.cards_grid.addWidget(card, row, col)

    def _render_seller_claims(self) -> None:
        # Clear previous claims widgets
        while self.claims_container.count():
            item = self.claims_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._claims or not self._claims.has_claims:
            return

        report = self._claims_matcher.compare(self._claims, self._results)
        card = QFrame()
        card.setObjectName("cardFrame")
        card.setStyleSheet("""
            QFrame#cardFrame {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel(f"📋 Seller Advertised Claims Verification ({report.matches_count}/{len(report.items)} Matched)")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #38BDF8;")
        header.addWidget(title)
        header.addStretch()

        badge_txt = "✓ ALL CLAIMS MATCH" if report.all_matched else f"⚠ {report.mismatches_count} MISMATCH(ES)"
        badge = QLabel(badge_txt)
        badge.setStyleSheet(
            "background-color: #064E3B; color: #34D399; font-weight: 700; padding: 4px 10px; border-radius: 6px; font-size: 11px;"
            if report.all_matched else
            "background-color: #7F1D1D; color: #F87171; font-weight: 700; padding: 4px 10px; border-radius: 6px; font-size: 11px;"
        )
        header.addWidget(badge)
        layout.addLayout(header)

        # Table of claim comparisons
        table = QTableWidget(len(report.items), 4)
        table.setHorizontalHeaderLabels(["Component", "Advertised Claim", "Detected Hardware", "Match Verdict"])
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table.setStyleSheet("""
            QTableWidget {
                background-color: #0F172A;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 6px;
                gridline-color: #1E293B;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #1E293B;
                color: #94A3B8;
                font-weight: 600;
                padding: 6px;
                border: none;
            }
        """)

        for row, it in enumerate(report.items):
            table.setItem(row, 0, QTableWidgetItem(it.component))
            table.setItem(row, 1, QTableWidgetItem(it.claimed_value))
            actual_item = QTableWidgetItem(f"{it.actual_value} — {it.details}")
            table.setItem(row, 2, actual_item)

            v_item = QTableWidgetItem("✓ Match" if it.is_match else "✕ Mismatch")
            if it.is_match:
                v_item.setForeground(Qt.GlobalColor.green)
            else:
                v_item.setForeground(Qt.GlobalColor.red)
            table.setItem(row, 3, v_item)

        table.setFixedHeight(min(220, 36 + len(report.items) * 32))
        layout.addWidget(table)

        self.claims_container.addWidget(card)

    def _render_red_flags(self, summary: ScoringSummary) -> None:
        # Clear old red flags
        while self.red_flags_container.count():
            item = self.red_flags_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not summary.red_flags and not summary.recommendations:
            return

        has_fail = summary.verdict == "LOW"
        rf_box = QFrame()
        rf_box.setObjectName("dangerCard" if has_fail else "highlightCard")
        rf_box.setStyleSheet(
            "background-color: rgba(220, 38, 38, 0.12); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 10px; padding: 14px;"
            if has_fail else
            "background-color: rgba(217, 119, 6, 0.12); border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 10px; padding: 14px;"
        )

        rf_box_layout = QVBoxLayout(rf_box)
        rf_box_layout.setContentsMargins(14, 12, 14, 12)
        rf_box_layout.setSpacing(6)

        rf_title = QLabel("🚩 Potential Issues & Actionable Buyer Notes:")
        rf_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #EF4444;" if has_fail else "font-size: 14px; font-weight: 700; color: #F59E0B;")
        rf_box_layout.addWidget(rf_title)

        for flag in summary.red_flags:
            lbl = QLabel(f"• <b>Flag:</b> {flag}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #F8FAFC; font-size: 12px;")
            rf_box_layout.addWidget(lbl)

        for rec in summary.recommendations:
            lbl = QLabel(f"• <b>Tip:</b> {rec}")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #93C5FD; font-size: 12px;")
            rf_box_layout.addWidget(lbl)

        self.red_flags_container.addWidget(rf_box)
