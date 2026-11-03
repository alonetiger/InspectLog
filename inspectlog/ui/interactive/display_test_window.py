"""Fullscreen display diagnostic window for dead pixels, backlight bleed, and gradient banding."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QLinearGradient,
    QPaintEvent,
    QPainter,
    QPen,
)
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from inspectlog.infra.logging import get_logger

logger = get_logger("display_test_window")


@dataclass
class DisplayPattern:
    """A visual pattern in the fullscreen test sequence."""

    name: str
    pattern_type: str  # "solid" or "gradient"
    color: QColor
    instructions: str
    check_target: str


PATTERNS: list[DisplayPattern] = [
    DisplayPattern(
        name="Pure Red",
        pattern_type="solid",
        color=QColor(255, 0, 0),
        instructions="Look for dark/black spots (dead red subpixels) or off-color dots.",
        check_target="Dead Red Subpixels",
    ),
    DisplayPattern(
        name="Pure Green",
        pattern_type="solid",
        color=QColor(0, 255, 0),
        instructions="Look for dark/black spots (dead green subpixels) or off-color dots.",
        check_target="Dead Green Subpixels",
    ),
    DisplayPattern(
        name="Pure Blue",
        pattern_type="solid",
        color=QColor(0, 0, 255),
        instructions="Look for dark/black spots (dead blue subpixels) or off-color dots.",
        check_target="Dead Blue Subpixels",
    ),
    DisplayPattern(
        name="Pure Black",
        pattern_type="solid",
        color=QColor(0, 0, 0),
        instructions="Check for bright stuck pixels (colored or white) and backlight bleed along screen edges.",
        check_target="Stuck Pixels & Backlight Bleed",
    ),
    DisplayPattern(
        name="Pure White",
        pattern_type="solid",
        color=QColor(255, 255, 255),
        instructions="Check for dark dead pixels, dirty screen effect, and yellowing/vignetting in corners.",
        check_target="Dark Dead Pixels & Brightness Uniformity",
    ),
    DisplayPattern(
        name="50% Neutral Grey",
        pattern_type="solid",
        color=QColor(128, 128, 128),
        instructions="Check panel uniformity, clouding, and IPS glow across the display area.",
        check_target="Panel Uniformity & Glow",
    ),
    DisplayPattern(
        name="256-Level Greyscale Gradient",
        pattern_type="gradient",
        color=QColor(0, 0, 0),
        instructions="Verify smooth transitions from pure black to pure white without harsh vertical bands or dithering noise.",
        check_target="Color Depth & Banding",
    ),
]


class DisplayTestResult:
    """Records the outcome of the fullscreen display test."""

    def __init__(self) -> None:
        self.completed: bool = False
        self.defects: list[str] = []
        self.passed_slides: int = 0
        self.total_slides: int = len(PATTERNS)

    @property
    def passed(self) -> bool:
        return len(self.defects) == 0

    def summary_text(self) -> str:
        if not self.completed and not self.defects:
            return "Test Cancelled (Incomplete)"
        if self.passed:
            return f"Passed: Clean ({self.passed_slides}/{self.total_slides} patterns verified, 0 defects)"
        return f"Warning: {len(self.defects)} defect(s) flagged ({', '.join(self.defects)})"


class DisplayTestWindow(QDialog):
    """Fullscreen modal window cycling through diagnostic display test patterns."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._current_index = 0
        self._show_hud = True
        self._result = DisplayTestResult()

        # Layout for floating HUD overlay
        self._init_ui()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.addStretch()

        # Floating HUD container
        self.hud_card = QWidget(self)
        self.hud_card.setObjectName("hudCard")
        self.hud_card.setStyleSheet("""
            QWidget#hudCard {
                background-color: rgba(20, 24, 33, 230);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 12px;
                padding: 16px;
            }
            QLabel {
                color: #FFFFFF;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
        """)

        hud_layout = QVBoxLayout(self.hud_card)
        hud_layout.setSpacing(8)

        # Header: Slide indicator + Defect status
        header_row = QHBoxLayout()
        self.lbl_title = QLabel("Pattern 1 of 7: Pure Red")
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #60A5FA;")
        header_row.addWidget(self.lbl_title)

        header_row.addStretch()

        self.lbl_status = QLabel("0 Defects Flagged")
        self.lbl_status.setStyleSheet("""
            background-color: #064E3B;
            color: #34D399;
            font-size: 12px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 6px;
        """)
        header_row.addWidget(self.lbl_status)
        hud_layout.addLayout(header_row)

        # Instructions
        self.lbl_instructions = QLabel(PATTERNS[0].instructions)
        self.lbl_instructions.setStyleSheet("font-size: 13px; color: #D1D5DB;")
        self.lbl_instructions.setWordWrap(True)
        hud_layout.addWidget(self.lbl_instructions)

        # Shortcut hints bar
        hints_row = QHBoxLayout()
        hints_row.setSpacing(12)

        hints = [
            ("Space / Enter", "Next Pattern"),
            ("P", "Mark Pass"),
            ("F", "Flag Defect"),
            ("H", "Hide/Show HUD"),
            ("Esc", "Finish Test"),
        ]
        for key, desc in hints:
            lbl_item = QLabel(f"<b style='color:#93C5FD;'>[{key}]</b> <span style='color:#9CA3AF;'>{desc}</span>")
            lbl_item.setStyleSheet("font-size: 11px;")
            hints_row.addWidget(lbl_item)

        hints_row.addStretch()

        # Quick action buttons for mouse / touch users
        self.btn_pass = QPushButton("✓ Pass")
        self.btn_pass.setStyleSheet("""
            QPushButton {
                background-color: #059669;
                color: white;
                font-weight: 600;
                font-size: 12px;
                padding: 6px 14px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #10B981; }
        """)
        self.btn_pass.clicked.connect(self._mark_pass)
        hints_row.addWidget(self.btn_pass)

        self.btn_fail = QPushButton("⚠ Flag Defect")
        self.btn_fail.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: white;
                font-weight: 600;
                font-size: 12px;
                padding: 6px 14px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #EF4444; }
        """)
        self.btn_fail.clicked.connect(self._flag_defect)
        hints_row.addWidget(self.btn_fail)

        hud_layout.addLayout(hints_row)

        main_layout.addWidget(self.hud_card, alignment=Qt.AlignmentFlag.AlignHCenter)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint fullscreen diagnostic pattern behind the HUD."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        rect = self.rect()

        pattern = PATTERNS[self._current_index]

        if pattern.pattern_type == "solid":
            painter.fillRect(rect, pattern.color)
        elif pattern.pattern_type == "gradient":
            grad = QLinearGradient(0, 0, rect.width(), 0)
            grad.setColorAt(0.0, QColor(0, 0, 0))
            grad.setColorAt(1.0, QColor(255, 255, 255))
            painter.fillRect(rect, grad)

        painter.end()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle keyboard navigation and verdict confirmation."""
        key = event.key()

        if key in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Right, Qt.Key.Key_PageDown):
            self._next_pattern()
        elif key in (Qt.Key.Key_Left, Qt.Key.Key_PageUp):
            self._prev_pattern()
        elif key == Qt.Key.Key_P:
            self._mark_pass()
        elif key == Qt.Key.Key_F:
            self._flag_defect()
        elif key == Qt.Key.Key_H:
            self._toggle_hud()
        elif key == Qt.Key.Key_Escape:
            self._finish_test()
        else:
            super().keyPressEvent(event)

    def _next_pattern(self) -> None:
        if self._current_index < len(PATTERNS) - 1:
            self._current_index += 1
            self._update_display()
        else:
            self._finish_test()

    def _prev_pattern(self) -> None:
        if self._current_index > 0:
            self._current_index -= 1
            self._update_display()

    def _mark_pass(self) -> None:
        self._result.passed_slides += 1
        self._next_pattern()

    def _flag_defect(self) -> None:
        curr = PATTERNS[self._current_index]
        defect_msg = f"{curr.name} ({curr.check_target})"
        if defect_msg not in self._result.defects:
            self._result.defects.append(defect_msg)

        # Update badge
        count = len(self._result.defects)
        self.lbl_status.setText(f"{count} Defect(s) Flagged")
        self.lbl_status.setStyleSheet("""
            background-color: #7F1D1D;
            color: #F87171;
            font-size: 12px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 6px;
        """)

        self._next_pattern()

    def _toggle_hud(self) -> None:
        self._show_hud = not self._show_hud
        self.hud_card.setVisible(self._show_hud)

    def _update_display(self) -> None:
        curr = PATTERNS[self._current_index]
        self.lbl_title.setText(f"Pattern {self._current_index + 1} of {len(PATTERNS)}: {curr.name}")
        self.lbl_instructions.setText(curr.instructions)
        self.update()  # Triggers paintEvent

    def _finish_test(self) -> None:
        self._result.completed = True
        logger.info(
            "Display test completed: %d defects flagged across %d patterns",
            len(self._result.defects),
            len(PATTERNS),
        )
        self.accept()

    def get_result(self) -> DisplayTestResult:
        """Return the result recorded during testing."""
        return self._result

    @classmethod
    def execute_test(cls, parent: QWidget | None = None) -> DisplayTestResult:
        """Run the display test sequence modally in fullscreen and return the result."""
        dlg = cls(parent)
        dlg.showFullScreen()
        dlg.exec()
        return dlg.get_result()
