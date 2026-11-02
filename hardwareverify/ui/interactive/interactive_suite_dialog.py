"""Interactive Diagnostics Suite Hub containing all guided hardware testing modules."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from hardwareverify.core.models import Confidence, DataSource, ModuleResult, Status, VerifiedValue
from hardwareverify.infra.logging import get_logger
from hardwareverify.ui.interactive.display_test_window import DisplayTestResult, DisplayTestWindow
from hardwareverify.ui.interactive.keyboard_test_widget import KeyboardTestWidget
from hardwareverify.ui.interactive.mic_test_widget import MicTestWidget
from hardwareverify.ui.interactive.mouse_test_widget import MouseTestWidget
from hardwareverify.ui.interactive.speaker_test_widget import SpeakerTestWidget
from hardwareverify.ui.interactive.usb_port_widget import USBPortWidget
from hardwareverify.ui.interactive.webcam_test_widget import WebcamTestWidget

logger = get_logger("interactive_suite")


class InteractiveSuiteDialog(QDialog):
    """Unified modal container for all interactive and guided hardware tests."""

    suite_completed = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("HardwareVerify — Guided Interactive Diagnostics")
        self.resize(920, 680)
        self.setMinimumSize(800, 580)
        self.setStyleSheet("""
            QDialog {
                background-color: #0F172A;
                color: #F8FAFC;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid #334155;
                background-color: #1E293B;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #0F172A;
                color: #94A3B8;
                padding: 10px 18px;
                font-size: 13px;
                font-weight: 600;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background-color: #1E293B;
                color: #38BDF8;
                border: 1px solid #334155;
                border-bottom: none;
            }
            QTabBar::tab:hover:!selected {
                background-color: #1E293B;
                color: #E2E8F0;
            }
        """)

        self._display_result: DisplayTestResult | None = None
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Top Bar
        top_bar = QHBoxLayout()
        lbl_header = QLabel("Guided Interactive Diagnostics")
        lbl_header.setStyleSheet("font-size: 20px; font-weight: 800; color: #F8FAFC;")
        top_bar.addWidget(lbl_header)

        top_bar.addStretch()

        self.btn_done = QPushButton("✓ Save & Return to Results")
        self.btn_done.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: white;
                font-weight: 700;
                font-size: 13px;
                padding: 8px 20px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #0369A1; }
        """)
        self.btn_done.clicked.connect(self._finish_suite)
        top_bar.addWidget(self.btn_done)

        main_layout.addLayout(top_bar)

        # Tab Widget
        self.tabs = QTabWidget(self)

        # Tab 0: Display Test Launcher
        self.tab_display = self._build_display_tab()
        self.tabs.addTab(self.tab_display, "🖥️ Display")

        # Tab 1: Keyboard
        self.tab_keyboard = KeyboardTestWidget(self)
        self.tabs.addTab(self.tab_keyboard, "⌨️ Keyboard")

        # Tab 2: Mouse & Touchpad
        self.tab_mouse = MouseTestWidget(self)
        self.tabs.addTab(self.tab_mouse, "🖱️ Mouse / Touchpad")

        # Tab 3: Speakers
        self.tab_speakers = SpeakerTestWidget(self)
        self.tabs.addTab(self.tab_speakers, "🔊 Speakers")

        # Tab 4: Microphone
        self.tab_mic = MicTestWidget(self)
        self.tabs.addTab(self.tab_mic, "🎙️ Microphone")

        # Tab 5: Webcam
        self.tab_webcam = WebcamTestWidget(self)
        self.tabs.addTab(self.tab_webcam, "📷 Webcam")

        # Tab 6: USB Ports
        self.tab_usb = USBPortWidget(self)
        self.tabs.addTab(self.tab_usb, "🔌 USB Ports")

        main_layout.addWidget(self.tabs, 1)

    def _build_display_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        lbl_title = QLabel("Fullscreen Display Quality & Pixel Inspection")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #E2E8F0;")
        layout.addWidget(lbl_title)

        desc = QLabel(
            "The display diagnostic switches your screen to full-screen solid RGB, pure black, "
            "pure white, 50% grey, and smooth 256-level greyscale gradients. "
            "This lets you detect stuck pixels, dead subpixels, edge backlight bleed, and color banding.\n\n"
            "Press [Space] to advance slides, [P] to pass, [F] to flag defects, and [Esc] to exit."
        )
        desc.setStyleSheet("color: #94A3B8; font-size: 13px; line-height: 1.5;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Launch card
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 24px;
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(14)

        self.btn_launch_display = QPushButton("🖥️ Launch Fullscreen Display Test")
        self.btn_launch_display.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: white;
                font-weight: 700;
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover { background-color: #10B981; }
        """)
        self.btn_launch_display.clicked.connect(self._launch_display_test)
        card_layout.addWidget(self.btn_launch_display, alignment=Qt.AlignmentFlag.AlignLeft)

        self.lbl_disp_status = QLabel("Status: Not Executed Yet")
        self.lbl_disp_status.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: 600;")
        card_layout.addWidget(self.lbl_disp_status)

        layout.addWidget(card)
        layout.addStretch()
        return widget

    def _launch_display_test(self) -> None:
        self._display_result = DisplayTestWindow.execute_test(self)
        if self._display_result:
            summary = self._display_result.summary_text()
            self.lbl_disp_status.setText(f"Status: {summary}")
            if self._display_result.passed:
                self.lbl_disp_status.setStyleSheet("color: #10B981; font-size: 13px; font-weight: 700;")
            else:
                self.lbl_disp_status.setStyleSheet("color: #EF4444; font-size: 13px; font-weight: 700;")

    def _finish_suite(self) -> None:
        results = self.collect_all_results()
        self.suite_completed.emit(results)
        self.accept()

    def collect_all_results(self) -> dict[str, Any]:
        """Collect structured verification summaries across all test tabs."""
        return {
            "display": self._display_result.summary_text() if self._display_result else "Not Tested",
            "keyboard": self.tab_keyboard.get_test_summary(),
            "mouse": self.tab_mouse.get_test_summary(),
            "speakers": self.tab_speakers.get_test_summary(),
            "microphone": self.tab_mic.get_test_summary(),
            "webcam": self.tab_webcam.get_test_summary(),
            "usb_ports": self.tab_usb.get_test_summary(),
        }

    def apply_results_to_modules(
        self,
        display_results: list[ModuleResult],
        input_result: ModuleResult,
    ) -> None:
        """Update live ModuleResult objects with the outcomes of interactive testing."""
        all_data = self.collect_all_results()

        # Update Display Result
        disp_summary = all_data["display"]
        for dr in display_results:
            if self._display_result and self._display_result.completed:
                if self._display_result.passed:
                    dr.readings["pixel_defect_test"] = VerifiedValue(
                        value="Passed (0 defects detected across 7 patterns)",
                        confidence=Confidence.HIGH,
                        sources=[DataSource(name="DisplayTestWindow", raw_value="User verified 7/7 patterns")],
                    )
                else:
                    dr.readings["pixel_defect_test"] = VerifiedValue(
                        value=f"Defects Flagged ({len(self._display_result.defects)}): {', '.join(self._display_result.defects)}",
                        confidence=Confidence.HIGH,
                        sources=[DataSource(name="DisplayTestWindow", raw_value=self._display_result.defects)],
                    )
                    dr.deduct_score(25, f"Display defects reported: {', '.join(self._display_result.defects)}")

        # Update Input Result
        kb = all_data["keyboard"]
        mouse = all_data["mouse"]
        spk = all_data["speakers"]
        mic = all_data["microphone"]
        cam = all_data["webcam"]
        usb = all_data["usb_ports"]

        summary_parts = []
        if kb.get("passed"):
            summary_parts.append(f"Keyboard ({kb['verified_keys']} keys)")
        if mouse.get("passed"):
            summary_parts.append("Mouse/Touchpad")
        if spk.get("passed"):
            summary_parts.append("Stereo Speakers")
        if mic.get("passed"):
            summary_parts.append("Microphone")
        if cam.get("passed"):
            summary_parts.append("Webcam")
        if usb.get("passed"):
            summary_parts.append(f"USB ({usb['verified_ports_count']} ports)")

        if summary_parts:
            status_text = f"Verified: {', '.join(summary_parts)}"
            input_result.readings["interactive_tests"] = VerifiedValue(
                value=status_text,
                confidence=Confidence.HIGH,
                sources=[DataSource(name="InteractiveSuite", raw_value=all_data)],
            )
            input_result.finalize(input_result.test_duration)
