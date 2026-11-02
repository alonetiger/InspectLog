"""Tooltip and provenance information label widget."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from hardwareverify.core.models import READING_TOOLTIPS, VerifiedValue


class TooltipLabel(QWidget):
    """Displays a metric title with an interactive info tooltip explaining the metric."""

    def __init__(
        self,
        key_name: str,
        display_title: str,
        custom_tooltip: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.title_label = QLabel(display_title)
        self.title_label.setObjectName("textSecondary")
        layout.addWidget(self.title_label)

        # Info icon
        self.icon_label = QLabel("ⓘ")
        self.icon_label.setObjectName("textMuted")
        self.icon_label.setCursor(Qt.CursorShape.PointingHandCursor)

        tooltip_text = custom_tooltip or READING_TOOLTIPS.get(
            key_name, "Information regarding this hardware component reading."
        )
        self.icon_label.setToolTip(tooltip_text)
        layout.addWidget(self.icon_label)
        layout.addStretch()


class ValueDisplayWidget(QWidget):
    """Displays a reading value along with its data provenance tooltip."""

    def __init__(self, verified: VerifiedValue, parent=None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.val_label = QLabel()
        if verified.is_available:
            self.val_label.setText(str(verified.value))
            self.val_label.setStyleSheet("font-weight: 600;")
        else:
            reason = verified.unavailable_reason or "Hardware/driver did not return value"
            self.val_label.setText("Unavailable")
            self.val_label.setStyleSheet("font-style: italic; color: #94a3b8;")
            self.val_label.setToolTip(f"Why unavailable: {reason}")

        # Assemble provenance tooltip for data sources
        sources_info: list[str] = []
        for s in verified.sources:
            sources_info.append(f"• Source: {s.name}\n  Raw: {s.raw_value}")

        if sources_info:
            full_tooltip = "Data Sources & Provenance:\n" + "\n".join(sources_info)
            if verified.unavailable_reason:
                full_tooltip = f"Reason Unavailable: {verified.unavailable_reason}\n\n" + full_tooltip
            self.val_label.setToolTip(full_tooltip)

        layout.addWidget(self.val_label)
        layout.addStretch()
