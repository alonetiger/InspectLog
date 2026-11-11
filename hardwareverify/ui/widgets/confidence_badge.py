"""Confidence level badge widget."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from hardwareverify.core.models import Confidence
from hardwareverify.ui.theme import ThemeManager


class ConfidenceBadge(QLabel):
    """Pill-shaped badge indicating data confidence level."""

    def __init__(self, confidence: Confidence = Confidence.MEDIUM, parent=None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_confidence(confidence)

    def set_confidence(self, confidence: Confidence) -> None:
        text = confidence.value.upper()
        tone = {Confidence.HIGH: "success", Confidence.MEDIUM: "warning"}.get(confidence, "danger")
        colors = ThemeManager.get_colors()

        self.setText(text)
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {colors[f"tint_{tone}"]};
                color: {colors[f"accent_{tone}"]};
                border: 1px solid {colors[f"rim_{tone}"]};
                border-radius: 9px;
                font-size: 10px;
                font-weight: 700;
                padding: 2px 8px;
                min-width: 50px;
            }}
        """)
