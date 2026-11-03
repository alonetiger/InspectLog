"""Interactive keyboard tester with visual ANSI layout and live state tracking."""

from __future__ import annotations

from typing import NamedTuple

from PySide6.QtCore import QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from inspectlog.infra.logging import get_logger

logger = get_logger("keyboard_test_widget")


class KeyDef(NamedTuple):
    """Specification of an interactive key on the keyboard canvas."""

    label: str
    width: float  # Multiplier relative to standard key (1.0 = 1U)
    qt_key: int


# ANSI standard 80-key compact layout
KEY_ROWS: list[list[KeyDef]] = [
    # Row 0: Function Keys
    [
        KeyDef("Esc", 1.0, Qt.Key.Key_Escape),
        KeyDef("F1", 1.0, Qt.Key.Key_F1),
        KeyDef("F2", 1.0, Qt.Key.Key_F2),
        KeyDef("F3", 1.0, Qt.Key.Key_F3),
        KeyDef("F4", 1.0, Qt.Key.Key_F4),
        KeyDef("F5", 1.0, Qt.Key.Key_F5),
        KeyDef("F6", 1.0, Qt.Key.Key_F6),
        KeyDef("F7", 1.0, Qt.Key.Key_F7),
        KeyDef("F8", 1.0, Qt.Key.Key_F8),
        KeyDef("F9", 1.0, Qt.Key.Key_F9),
        KeyDef("F10", 1.0, Qt.Key.Key_F10),
        KeyDef("F11", 1.0, Qt.Key.Key_F11),
        KeyDef("F12", 1.0, Qt.Key.Key_F12),
        KeyDef("PrtSc", 1.0, Qt.Key.Key_Print),
        KeyDef("Del", 1.0, Qt.Key.Key_Delete),
    ],
    # Row 1: Numbers
    [
        KeyDef("`", 1.0, Qt.Key.Key_QuoteLeft),
        KeyDef("1", 1.0, Qt.Key.Key_1),
        KeyDef("2", 1.0, Qt.Key.Key_2),
        KeyDef("3", 1.0, Qt.Key.Key_3),
        KeyDef("4", 1.0, Qt.Key.Key_4),
        KeyDef("5", 1.0, Qt.Key.Key_5),
        KeyDef("6", 1.0, Qt.Key.Key_6),
        KeyDef("7", 1.0, Qt.Key.Key_7),
        KeyDef("8", 1.0, Qt.Key.Key_8),
        KeyDef("9", 1.0, Qt.Key.Key_9),
        KeyDef("0", 1.0, Qt.Key.Key_0),
        KeyDef("-", 1.0, Qt.Key.Key_Minus),
        KeyDef("=", 1.0, Qt.Key.Key_Equal),
        KeyDef("Backspace", 2.0, Qt.Key.Key_Backspace),
    ],
    # Row 2: QWERTY
    [
        KeyDef("Tab", 1.5, Qt.Key.Key_Tab),
        KeyDef("Q", 1.0, Qt.Key.Key_Q),
        KeyDef("W", 1.0, Qt.Key.Key_W),
        KeyDef("E", 1.0, Qt.Key.Key_E),
        KeyDef("R", 1.0, Qt.Key.Key_R),
        KeyDef("T", 1.0, Qt.Key.Key_T),
        KeyDef("Y", 1.0, Qt.Key.Key_Y),
        KeyDef("U", 1.0, Qt.Key.Key_U),
        KeyDef("I", 1.0, Qt.Key.Key_I),
        KeyDef("O", 1.0, Qt.Key.Key_O),
        KeyDef("P", 1.0, Qt.Key.Key_P),
        KeyDef("[", 1.0, Qt.Key.Key_BracketLeft),
        KeyDef("]", 1.0, Qt.Key.Key_BracketRight),
        KeyDef("\\", 1.5, Qt.Key.Key_Backslash),
    ],
    # Row 3: Home Row
    [
        KeyDef("Caps", 1.75, Qt.Key.Key_CapsLock),
        KeyDef("A", 1.0, Qt.Key.Key_A),
        KeyDef("S", 1.0, Qt.Key.Key_S),
        KeyDef("D", 1.0, Qt.Key.Key_D),
        KeyDef("F", 1.0, Qt.Key.Key_F),
        KeyDef("G", 1.0, Qt.Key.Key_G),
        KeyDef("H", 1.0, Qt.Key.Key_H),
        KeyDef("J", 1.0, Qt.Key.Key_J),
        KeyDef("K", 1.0, Qt.Key.Key_K),
        KeyDef("L", 1.0, Qt.Key.Key_L),
        KeyDef(";", 1.0, Qt.Key.Key_Semicolon),
        KeyDef("'", 1.0, Qt.Key.Key_Apostrophe),
        KeyDef("Enter", 2.25, Qt.Key.Key_Return),
    ],
    # Row 4: Shift Row
    [
        KeyDef("Shift", 2.25, Qt.Key.Key_Shift),
        KeyDef("Z", 1.0, Qt.Key.Key_Z),
        KeyDef("X", 1.0, Qt.Key.Key_X),
        KeyDef("C", 1.0, Qt.Key.Key_C),
        KeyDef("V", 1.0, Qt.Key.Key_V),
        KeyDef("B", 1.0, Qt.Key.Key_B),
        KeyDef("N", 1.0, Qt.Key.Key_N),
        KeyDef("M", 1.0, Qt.Key.Key_M),
        KeyDef(",", 1.0, Qt.Key.Key_Comma),
        KeyDef(".", 1.0, Qt.Key.Key_Period),
        KeyDef("/", 1.0, Qt.Key.Key_Slash),
        KeyDef("Shift", 1.75, Qt.Key.Key_Shift),
        KeyDef("▲", 1.0, Qt.Key.Key_Up),
    ],
    # Row 5: Modifiers & Space
    [
        KeyDef("Ctrl", 1.25, Qt.Key.Key_Control),
        KeyDef("Win", 1.25, Qt.Key.Key_Meta),
        KeyDef("Alt", 1.25, Qt.Key.Key_Alt),
        KeyDef("Space", 6.25, Qt.Key.Key_Space),
        KeyDef("Alt", 1.25, Qt.Key.Key_Alt),
        KeyDef("Ctrl", 1.25, Qt.Key.Key_Control),
        KeyDef("◄", 1.0, Qt.Key.Key_Left),
        KeyDef("▼", 1.0, Qt.Key.Key_Down),
        KeyDef("►", 1.0, Qt.Key.Key_Right),
    ],
]


class KeyboardCanvas(QWidget):
    """Custom painted visual keyboard representation."""

    key_verified = Signal(int, int)  # (verified_count, total_count)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(780, 260)

        # State tracking
        self.pressed_keys: set[int] = set()
        self.verified_keys: set[int] = set()

        # Count total unique keys
        all_keys: set[int] = set()
        for row in KEY_ROWS:
            for k in row:
                all_keys.add(k.qt_key)
        self.total_unique_keys = len(all_keys)

    def reset_test(self) -> None:
        """Reset verified keys state."""
        self.pressed_keys.clear()
        self.verified_keys.clear()
        self.update()
        self.key_verified.emit(0, self.total_unique_keys)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        self.pressed_keys.add(key)
        self.verified_keys.add(key)
        self.update()
        self.key_verified.emit(len(self.verified_keys), self.total_unique_keys)
        event.accept()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        self.pressed_keys.discard(key)
        self.update()
        event.accept()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        w = self.width()
        h = self.height()
        margin = 12
        spacing = 5

        num_rows = len(KEY_ROWS)
        row_height = (h - 2 * margin - (num_rows - 1) * spacing) / num_rows

        font = QFont("Segoe UI", 9, QFont.Weight.DemiBold)
        painter.setFont(font)

        y = margin
        for row in KEY_ROWS:
            total_units = sum(k.width for k in row)
            unit_width = (w - 2 * margin - (len(row) - 1) * spacing) / total_units

            x = margin
            for k in row:
                kw = k.width * unit_width
                rect = QRectF(x, y, kw, row_height)

                # Determine key color state
                if k.qt_key in self.pressed_keys:
                    bg_color = QColor(56, 189, 248)    # Active pressed: Cyan
                    text_color = QColor(15, 23, 42)
                    border_color = QColor(186, 230, 253)
                elif k.qt_key in self.verified_keys:
                    bg_color = QColor(16, 185, 129)    # Verified: Emerald Green
                    text_color = QColor(255, 255, 255)
                    border_color = QColor(52, 211, 153)
                else:
                    bg_color = QColor(30, 41, 59)      # Unverified: Slate Dark
                    text_color = QColor(148, 163, 184)
                    border_color = QColor(51, 65, 85)

                painter.setPen(QPen(border_color, 1))
                painter.setBrush(bg_color)
                painter.drawRoundedRect(rect, 5, 5)

                # Draw label
                painter.setPen(text_color)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, k.label)

                x += kw + spacing
            y += row_height + spacing

        painter.end()


class KeyboardTestWidget(QWidget):
    """Complete Keyboard testing tab with progress stats and instructions."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        # Header info
        header_row = QHBoxLayout()
        self.lbl_title = QLabel("Keyboard Functionality Test")
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #E2E8F0;")
        header_row.addWidget(self.lbl_title)

        header_row.addStretch()

        self.lbl_counter = QLabel("0 / 64 Keys Verified (0%)")
        self.lbl_counter.setStyleSheet("""
            background-color: #1E293B;
            color: #38BDF8;
            font-size: 13px;
            font-weight: 600;
            padding: 6px 14px;
            border-radius: 8px;
            border: 1px solid #334155;
        """)
        header_row.addWidget(self.lbl_counter)
        layout.addLayout(header_row)

        desc = QLabel(
            "Press each physical key on your keyboard. Keys will light up cyan while held, "
            "and turn permanently green once registered. Verify that every key registers without sticking."
        )
        desc.setStyleSheet("color: #94A3B8; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Canvas
        self.canvas = KeyboardCanvas(self)
        self.canvas.key_verified.connect(self._on_key_verified)
        layout.addWidget(self.canvas)

        # Controls row
        ctrl_row = QHBoxLayout()
        self.btn_reset = QPushButton("Reset Test")
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #E2E8F0;
                font-weight: 600;
                padding: 6px 16px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        self.btn_reset.clicked.connect(self.canvas.reset_test)
        ctrl_row.addWidget(self.btn_reset)

        ctrl_row.addStretch()

        self.lbl_verdict = QLabel("Status: Testing...")
        self.lbl_verdict.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 600;")
        ctrl_row.addWidget(self.lbl_verdict)

        layout.addLayout(ctrl_row)

    def _on_key_verified(self, count: int, total: int) -> None:
        pct = int((count / total) * 100) if total > 0 else 0
        self.lbl_counter.setText(f"{count} / {total} Keys Verified ({pct}%)")

        if pct >= 80:
            self.lbl_verdict.setText("Status: ✓ Main Layout Verified")
            self.lbl_verdict.setStyleSheet("color: #10B981; font-size: 12px; font-weight: 600;")
            self.lbl_counter.setStyleSheet("""
                background-color: #064E3B;
                color: #34D399;
                font-size: 13px;
                font-weight: 600;
                padding: 6px 14px;
                border-radius: 8px;
            """)
        elif count > 0:
            self.lbl_verdict.setText(f"Status: In Progress ({count} registered)")
            self.lbl_verdict.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: 600;")

    def get_test_summary(self) -> dict[str, Any]:
        """Return verification outcome for report generation."""
        verified = len(self.canvas.verified_keys)
        total = self.canvas.total_unique_keys
        pct = int((verified / total) * 100) if total > 0 else 0
        return {
            "verified_keys": verified,
            "total_keys": total,
            "passed": pct >= 70,
            "coverage_pct": pct,
        }
