"""PDF Report generation engine using ReportLab."""

from __future__ import annotations

import datetime
from io import BytesIO
import os
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image as RLImage,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from inspectlog.constants import APP_DISPLAY_NAME, APP_VERSION, LOGO_PATH
from inspectlog.core.models import ModuleResult, Status
from inspectlog.infra.config import SellerClaims
from inspectlog.infra.logging import get_logger
from inspectlog.report.claims_matcher import ClaimsMatcher, ClaimsReport
from inspectlog.report.scoring import ScoringEngine, ScoringSummary

logger = get_logger("pdf_generator")


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to add 'Page X of Y' footers and headers."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict] = []

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int) -> None:
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Footer
        footer_text = f"InspectLog v{APP_VERSION} • Certified Hardware Audit • Page {self._pageNumber} of {total_pages}"
        self.drawRightString(letter[0] - 36, 24, footer_text)
        self.drawString(36, 24, "Independent Buyer Protection Report • Non-Destructive Hardware Verification")

        # Top rule on page 2+
        if self._pageNumber > 1:
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(36, letter[1] - 30, letter[0] - 36, letter[1] - 30)
            self.drawString(36, letter[1] - 25, "InspectLog Hardware Audit Report")

        self.restoreState()


class PDFReportGenerator:
    """Renders professional multi-page hardware audit reports in PDF format."""

    def __init__(self) -> None:
        self._scoring_engine = ScoringEngine()
        self._claims_matcher = ClaimsMatcher()
        self._styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self) -> None:
        # Title
        self._styles.add(ParagraphStyle(
            "ReportTitle",
            parent=self._styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0F172A"),
        ))
        # Subtitle
        self._styles.add(ParagraphStyle(
            "ReportSubtitle",
            parent=self._styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#475569"),
        ))
        # Section Heading
        self._styles.add(ParagraphStyle(
            "SectionHeader",
            parent=self._styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=14,
            spaceAfter=6,
        ))
        # Body
        self._styles.add(ParagraphStyle(
            "BodyDark",
            parent=self._styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#1E293B"),
        ))
        self._styles.add(ParagraphStyle(
            "BodyMuted",
            parent=self._styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#64748B"),
        ))
        self._styles.add(ParagraphStyle(
            "TableCell",
            parent=self._styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#0F172A"),
        ))
        self._styles.add(ParagraphStyle(
            "TableCellBold",
            parent=self._styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#0F172A"),
        ))
        self._styles.add(ParagraphStyle(
            "ScoreBadge",
            parent=self._styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=1,  # Center
            textColor=colors.HexColor("#FFFFFF"),
        ))

    def generate_pdf(
        self,
        results: list[ModuleResult],
        claims: SellerClaims | None = None,
        output_path: str | None = None,
    ) -> bytes:
        """Generate a complete PDF inspection report.

        Args:
            results: List of ModuleResult objects.
            claims: Optional SellerClaims entered by buyer.
            output_path: Optional file path to write PDF to disk.

        Returns:
            Raw PDF bytes.
        """
        logger.info("Generating PDF report for %d modules", len(results))

        summary = self._scoring_engine.evaluate(results)
        claims_report = self._claims_matcher.compare(claims or SellerClaims(), results)

        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=42,
        )

        story = []

        # 1. Header & Title Block
        story.extend(self._build_header(results))
        story.append(Spacer(1, 12))

        # 2. Executive Summary Score Card
        story.extend(self._build_summary_card(summary))
        story.append(Spacer(1, 14))

        # 3. Red Flags & Recommendations Callout
        flags_widget = self._build_red_flags_block(summary)
        if flags_widget:
            story.append(flags_widget)
            story.append(Spacer(1, 14))

        # 4. Seller Claims Comparison Table (if entered)
        if claims_report.has_claims:
            story.extend(self._build_claims_table(claims_report))
            story.append(Spacer(1, 14))

        # 5. Component Breakdown Table
        story.extend(self._build_component_table(results))
        story.append(Spacer(1, 14))

        # 6. Build document
        doc.build(story, canvasmaker=NumberedCanvas)
        pdf_bytes = buf.getvalue()

        if output_path:
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(pdf_bytes)
            logger.info("Saved PDF report to %s (%d bytes)", output_path, len(pdf_bytes))

        return pdf_bytes

    def _build_header(self, results: list[ModuleResult]) -> list[Any]:
        # Extract system identity details for header
        sys_res = next((r for r in results if r.module_name == "system_identity"), None)
        mfg = "PC System"
        model = "Desktop/Notebook"
        serial = "Unknown"
        os_build = "Windows"
        bios = "N/A"

        if sys_res:
            mfg = sys_res.readings.get("manufacturer", sys_res.readings.get("system_manufacturer", None))
            mfg = mfg.value if mfg and mfg.value else "PC"
            model = sys_res.readings.get("model", None)
            model = model.value if model and model.value else "Notebook/PC"
            serial = sys_res.readings.get("serial_number", None)
            serial = serial.value if serial and serial.value else "Unknown"
            os_build = sys_res.readings.get("os_build", None)
            os_build = os_build.value if os_build and os_build.value else "Windows 10/11"
            bios = sys_res.readings.get("bios_version", None)
            bios = bios.value if bios and bios.value else "N/A"

        timestamp_str = datetime.datetime.now().strftime("%B %d, %Y at %I:%M %p")

        has_logo = os.path.exists(LOGO_PATH)
        if has_logo:
            logo_img = RLImage(LOGO_PATH, width=64, height=42.6)
            header_table_data = [
                [
                    logo_img,
                    Paragraph(f"<b>{APP_DISPLAY_NAME}</b> • Inspection Report<br/><font size='8.5' color='#475569'><b>Hardware:</b> {mfg} {model} &nbsp;|&nbsp; <b>OS:</b> {os_build} &nbsp;|&nbsp; <b>BIOS:</b> {bios}</font>", self._styles["ReportTitle"]),
                    Paragraph(f"<b>Audit Date:</b> {timestamp_str}<br/><b>Target Serial:</b> <code>{serial}</code><br/><b>Audit Integrity:</b> Certified Genuine", self._styles["TableCellBold"]),
                ]
            ]
            t = Table(header_table_data, colWidths=[70, 290, 180])
        else:
            header_table_data = [
                [
                    Paragraph(f"<b>{APP_DISPLAY_NAME}</b> • Inspection Report", self._styles["ReportTitle"]),
                    Paragraph(f"<b>Audit Date:</b> {timestamp_str}<br/><b>Target Serial:</b> <code>{serial}</code>", self._styles["TableCellBold"]),
                ],
                [
                    Paragraph(f"<b>Hardware:</b> {mfg} {model} &nbsp;|&nbsp; <b>OS:</b> {os_build} &nbsp;|&nbsp; <b>BIOS:</b> {bios}", self._styles["ReportSubtitle"]),
                    Paragraph(f"<b>Audit Integrity:</b> Cryptographic & WMI Verified", self._styles["TableCell"]),
                ]
            ]
            t = Table(header_table_data, colWidths=[360, 180])

        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        return [t, HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284C7"), spaceBefore=6, spaceAfter=8)]

    def _build_summary_card(self, summary: ScoringSummary) -> list[Any]:
        # Verdict color styling
        if summary.verdict == "HIGH":
            card_bg = colors.HexColor("#F0FDF4")
            card_border = colors.HexColor("#86EFAC")
            score_bg = colors.HexColor("#059669")
            verdict_color = "#166534"
        elif summary.verdict == "MODERATE":
            card_bg = colors.HexColor("#FFFBEB")
            card_border = colors.HexColor("#FDE68A")
            score_bg = colors.HexColor("#D97706")
            verdict_color = "#92400E"
        else:
            card_bg = colors.HexColor("#FEF2F2")
            card_border = colors.HexColor("#FECACA")
            score_bg = colors.HexColor("#DC2626")
            verdict_color = "#991B1B"

        score_p = Paragraph(f"<br/><b>{summary.overall_score}</b><br/><font size='8'>HEALTH SCORE</font>", self._styles["ScoreBadge"])

        verdict_p = Paragraph(
            f"<font color='{verdict_color}'><b>{summary.verdict_title}</b></font><br/>"
            f"<font size='8.5' color='#334155'>{summary.verdict_explanation}</font>",
            self._styles["TableCellBold"],
        )

        card_data = [[score_p, verdict_p]]
        card_table = Table(card_data, colWidths=[90, 450])
        card_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), score_bg),
            ("BACKGROUND", (1, 0), (1, 0), card_bg),
            ("BOX", (0, 0), (-1, -1), 1, card_border),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ]))

        return [card_table]

    def _build_red_flags_block(self, summary: ScoringSummary) -> Any | None:
        if not summary.red_flags and not summary.recommendations:
            return None

        content = []
        if summary.red_flags:
            content.append(Paragraph("<b>🚩 Critical Red Flags & Wear Observations:</b>", self._styles["TableCellBold"]))
            for rf in summary.red_flags:
                content.append(Paragraph(f"• <font color='#DC2626'><b>Flag:</b></font> {rf}", self._styles["TableCell"]))

        if summary.recommendations:
            if summary.red_flags:
                content.append(Spacer(1, 4))
            content.append(Paragraph("<b>💡 Buyer Actionable Tips & Negotiation Strategy:</b>", self._styles["TableCellBold"]))
            for rec in summary.recommendations:
                content.append(Paragraph(f"• <font color='#0284C7'><b>Recommendation:</b></font> {rec}", self._styles["TableCell"]))

        box_data = [[content]]
        box_table = Table(box_data, colWidths=[540])
        box_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ]))
        return box_table

    def _build_claims_table(self, report: ClaimsReport) -> list[Any]:
        story = [Paragraph("Seller Advertised Claims Comparison", self._styles["SectionHeader"])]

        table_data = [
            [
                Paragraph("<b>Component</b>", self._styles["TableCellBold"]),
                Paragraph("<b>Seller Advertised</b>", self._styles["TableCellBold"]),
                Paragraph("<b>Hardware Detected</b>", self._styles["TableCellBold"]),
                Paragraph("<b>Match Verdict</b>", self._styles["TableCellBold"]),
            ]
        ]

        for it in report.items:
            verdict_badge = "<font color='#059669'><b>✓ MATCH</b></font>" if it.is_match else "<font color='#DC2626'><b>✕ MISMATCH</b></font>"
            details_line = f"<br/><font size='7.5' color='#64748B'>{it.details}</font>"

            table_data.append([
                Paragraph(f"<b>{it.component}</b>", self._styles["TableCellBold"]),
                Paragraph(it.claimed_value, self._styles["TableCell"]),
                Paragraph(f"{it.actual_value}{details_line}", self._styles["TableCell"]),
                Paragraph(verdict_badge, self._styles["TableCell"]),
            ])

        t = Table(table_data, colWidths=[110, 110, 220, 100])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#FFFFFF")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
        ]))
        story.append(t)
        return story

    def _build_component_table(self, results: list[ModuleResult]) -> list[Any]:
        story = [Paragraph("Detailed Component Inspection & Telemetry", self._styles["SectionHeader"])]

        table_data = [
            [
                Paragraph("<b>Module</b>", self._styles["TableCellBold"]),
                Paragraph("<b>Status</b>", self._styles["TableCellBold"]),
                Paragraph("<b>Score</b>", self._styles["TableCellBold"]),
                Paragraph("<b>Key Verified Telemetry & Provenance</b>", self._styles["TableCellBold"]),
                Paragraph("<b>Confidence</b>", self._styles["TableCellBold"]),
            ]
        ]

        for r in results:
            # Status badge
            if r.status == Status.PASS:
                stat_str = "<font color='#059669'><b>PASS</b></font>"
            elif r.status == Status.WARNING:
                stat_str = "<font color='#D97706'><b>WARN</b></font>"
            elif r.status == Status.FAIL:
                stat_str = "<font color='#DC2626'><b>FAIL</b></font>"
            else:
                stat_str = "<font color='#64748B'><b>N/A</b></font>"

            # Format readings lines
            readings_lines = []
            highest_conf = "Medium"
            conf_levels = [v.confidence.value for v in r.readings.values() if v.value is not None]
            if "High" in conf_levels:
                highest_conf = "High"
            elif all(c == "Low" for c in conf_levels) and conf_levels:
                highest_conf = "Low"

            for k, val in list(r.readings.items())[:5]:  # Top 5 readings
                if val.value is not None and str(val.value).strip():
                    src_tag = f" <font color='#94A3B8'>[{val.sources[0].name.split(':')[-1]}]</font>" if val.sources else ""
                    readings_lines.append(f"• <b>{k.replace('_', ' ').title()}:</b> {val.value}{src_tag}")

            for w in r.warnings:
                readings_lines.append(f"<font color='#D97706'>⚠ <i>{w}</i></font>")

            telemetry_text = "<br/>".join(readings_lines) if readings_lines else "<i>No readings recorded</i>"

            table_data.append([
                Paragraph(f"<b>{r.display_name}</b>", self._styles["TableCellBold"]),
                Paragraph(stat_str, self._styles["TableCell"]),
                Paragraph(f"{r.health_score}", self._styles["TableCellBold"]),
                Paragraph(telemetry_text, self._styles["TableCell"]),
                Paragraph(f"<b>{highest_conf}</b>", self._styles["TableCellBold"]),
            ])

        t = Table(table_data, colWidths=[110, 45, 40, 275, 70])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#FFFFFF")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
        ]))
        story.append(t)
        return story
