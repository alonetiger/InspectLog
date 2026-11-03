"""Main application window managing navigation and scan lifecycle."""

from __future__ import annotations

import os
import time

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from inspectlog.constants import APP_DISPLAY_NAME, ICON_PATH, LOGO_PATH
from inspectlog.core.models import ModuleResult
from inspectlog.infra.config import AppConfig, ScanConfig
from inspectlog.infra.logging import get_logger
from inspectlog.report.json_exporter import JSONReportExporter
from inspectlog.report.pdf_generator import PDFReportGenerator
from inspectlog.tests_engine.orchestrator import ScanOrchestrator
from inspectlog.ui.pages.home_page import HomePage
from inspectlog.ui.pages.results_page import ResultsPage
from inspectlog.ui.pages.scan_page import ScanPage
from inspectlog.ui.theme import ThemeManager
from inspectlog.ui.widgets.claims_dialog import SellerClaimsDialog
from inspectlog.ui.widgets.consent_dialog import StressTestConsentDialog

logger = get_logger("main_window")


class MainWindow(QMainWindow):
    """Main desktop application window."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(APP_DISPLAY_NAME)
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        self.setMinimumSize(960, 680)
        self.resize(1100, 780)

        self._config = AppConfig()
        self._orchestrator = ScanOrchestrator(self)
        self._current_results: list[ModuleResult] = []

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        self.central_widget = QWidget(self)
        self.central_widget.setObjectName("centralWidget")
        self.setCentralWidget(self.central_widget)

        layout = QVBoxLayout(self.central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Multi-page stacked widget
        self.stacked_widget = QStackedWidget(self)
        layout.addWidget(self.stacked_widget)

        # Page 0: Home Page
        self.home_page = HomePage(self)
        self.stacked_widget.addWidget(self.home_page)

        # Page 1: Scan In-Progress Page
        self.scan_page = ScanPage(self)
        self.stacked_widget.addWidget(self.scan_page)

        # Page 2: Results Page
        self.results_page = ResultsPage(self)
        self.stacked_widget.addWidget(self.results_page)

        self.stacked_widget.setCurrentIndex(0)

    def _connect_signals(self) -> None:
        # Home Page actions
        self.home_page.check_pc_requested.connect(self._on_launch_quick_scan)
        self.home_page.quick_scan_requested.connect(self._on_launch_quick_scan)
        self.home_page.full_test_requested.connect(self._on_launch_full_test)
        self.home_page.seller_claims_requested.connect(self._on_seller_claims_requested)
        self.home_page.interactive_diagnostics_requested.connect(self._on_launch_interactive_diagnostics)
        self.home_page.theme_toggled.connect(self._on_toggle_theme)

        # Scan Page actions
        self.scan_page.scan_cancelled.connect(self._on_cancel_scan)
        self.scan_page.view_results_requested.connect(self._on_view_results)

        # Results Page actions
        self.results_page.check_pc_again_requested.connect(self._on_launch_quick_scan)
        self.results_page.new_scan_requested.connect(self._on_new_scan)
        self.results_page.export_pdf_requested.connect(self._on_export_pdf)
        self.results_page.export_json_requested.connect(self._on_export_json)
        self.results_page.guided_diagnostics_requested.connect(self._on_launch_interactive_diagnostics)
        self.results_page.claims_edit_requested.connect(self._on_seller_claims_requested)

        # Orchestrator background worker signals
        self._orchestrator.module_started.connect(self._on_module_started)
        self._orchestrator.module_completed.connect(self._on_module_completed)
        self._orchestrator.scan_progress.connect(self._on_scan_progress)
        self._orchestrator.scan_completed.connect(self._on_scan_completed)
        self._orchestrator.scan_cancelled.connect(self._on_scan_cancelled)

    def _on_launch_quick_scan(self) -> None:
        config = ScanConfig(quick_scan=True)
        self._start_scan(config)

    def _on_launch_full_test(self) -> None:
        dialog = StressTestConsentDialog(self)
        if dialog.exec() == StressTestConsentDialog.DialogCode.Accepted:
            config = ScanConfig(quick_scan=False)
            self._start_scan(config)

    def _start_scan(self, config: ScanConfig) -> None:
        modules_list = [
            ("system_identity", "System Identity", "🖥️"),
            ("battery", "Battery", "🔋"),
            ("storage", "Storage", "💾"),
            ("ram", "RAM", "🧠"),
            ("cpu", "CPU", "⚡"),
            ("gpu", "GPU", "🎮"),
            ("display", "Display", "🖥️"),
            ("thermals", "Thermals & Fans", "🌡️"),
            ("security", "Security & Locks", "🔒"),
            ("input_io", "Input & Peripherals", "🎮"),
        ]
        self._current_results = []
        self.scan_page.prepare_scan(modules_list)
        self.stacked_widget.setCurrentIndex(1)
        self._orchestrator.start_scan(config)

    def _on_launch_interactive_diagnostics(self) -> None:
        """Launch the guided interactive diagnostics suite."""
        from inspectlog.ui.interactive.interactive_suite_dialog import InteractiveSuiteDialog
        dialog = InteractiveSuiteDialog(self)
        if dialog.exec() == InteractiveSuiteDialog.DialogCode.Accepted:
            if self._current_results:
                displays = [r for r in self._current_results if r.module_name == "display"]
                inputs = [r for r in self._current_results if r.module_name == "input_io"]
                if inputs:
                    dialog.apply_results_to_modules(displays, inputs[0])
                    self.results_page.display_results(self._current_results)

    def _on_module_started(self, module_name: str, display_name: str) -> None:
        self.scan_page.update_module_started(module_name)

    def _on_module_completed(self, module_name: str, result: ModuleResult) -> None:
        has_warnings = bool(result.warnings)
        has_errors = bool(result.errors)
        self.scan_page.update_module_completed(module_name, has_warnings, has_errors)

    def _on_scan_progress(self, pct: int) -> None:
        self.scan_page.update_progress(pct)

    def _on_scan_completed(self, results: list[ModuleResult]) -> None:
        self._current_results = results
        self.scan_page.mark_scan_finished()
        # Automatically transition to results page with claims
        self.results_page.display_results(results, claims=self._config.seller_claims)
        self.stacked_widget.setCurrentIndex(2)

    def _on_scan_cancelled(self) -> None:
        QMessageBox.information(self, "Scan Cancelled", "The hardware verification scan was cancelled.")
        self.stacked_widget.setCurrentIndex(0)

    def _on_cancel_scan(self) -> None:
        self._orchestrator.cancel_scan()

    def _on_view_results(self) -> None:
        self.results_page.display_results(self._current_results, claims=self._config.seller_claims)
        self.stacked_widget.setCurrentIndex(2)

    def _on_new_scan(self) -> None:
        self.stacked_widget.setCurrentIndex(0)

    def _on_seller_claims_requested(self) -> None:
        dialog = SellerClaimsDialog(self._config.seller_claims, self)
        if dialog.exec() == SellerClaimsDialog.DialogCode.Accepted:
            if self._current_results:
                self.results_page.display_results(self._current_results, claims=self._config.seller_claims)

    def _on_export_pdf(self) -> None:
        if not self._current_results:
            QMessageBox.warning(self, "No Results", "No scan results available to export. Run a scan first.")
            return

        default_name = f"InspectLog_Report_{time.strftime('%Y%m%d_%H%M%S')}.pdf"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export PDF Inspection Report", default_name, "PDF Documents (*.pdf)"
        )
        if file_path:
            try:
                gen = PDFReportGenerator()
                gen.generate_pdf(self._current_results, claims=self._config.seller_claims, output_path=file_path)
                QMessageBox.information(
                    self,
                    "Report Exported",
                    f"Successfully saved certified PDF report to:\n{file_path}",
                )
            except Exception as e:
                logger.exception("Failed to export PDF: %s", e)
                QMessageBox.critical(self, "Export Failed", f"Could not generate PDF report:\n{e}")

    def _on_export_json(self) -> None:
        if not self._current_results:
            QMessageBox.warning(self, "No Results", "No scan results available to export. Run a scan first.")
            return

        default_name = f"InspectLog_Audit_{time.strftime('%Y%m%d_%H%M%S')}.json"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export JSON Hardware Audit", default_name, "JSON Files (*.json)"
        )
        if file_path:
            try:
                exporter = JSONReportExporter()
                exporter.export_json(self._current_results, claims=self._config.seller_claims, output_path=file_path)
                QMessageBox.information(
                    self,
                    "Audit Data Exported",
                    f"Successfully saved JSON audit data to:\n{file_path}",
                )
            except Exception as e:
                logger.exception("Failed to export JSON: %s", e)
                QMessageBox.critical(self, "Export Failed", f"Could not export JSON data:\n{e}")

    def _on_toggle_theme(self) -> None:
        app = QApplication.instance()
        if app:
            new_theme = "light" if ThemeManager.current_theme() == "dark" else "dark"
            ThemeManager.apply_theme(app, new_theme)
