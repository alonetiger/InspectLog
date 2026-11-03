"""Confidence level badge widget."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from inspectlog.core.models import Confidence


class ConfidenceBadge(QLabel):
    """Pill-shaped badge indicating data confidence level."""

    def __init__(self, confidence: Confidence = Confidence.MEDIUM, parent=None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_confidence(confidence)

    def set_confidence(self, confidence: Confidence) -> None:
        text = confidence.value.upper()
        if confidence == Confidence.HIGH:
            bg_color = "#065f46"
            text_color = "#34d399"
            border_color = "#059669"
        elif confidence == Confidence.MEDIUM:
            bg_color = "#78350f"
            text_color = "#fbbf24"
            border_color = "#d97706"
        else:
            bg_color = "#7f1d1d"
            text_color = "#f87171"
            border_color = "#dc2626"

        self.setText(f" {text} ")
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                font-size: 10px;
                font-weight: 700;
                padding: 1px 6px;
                min-width: 50px;
            }}
        """)
