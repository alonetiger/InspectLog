"""Module card widget displaying component telemetry, score, and warnings."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from inspectlog.core.models import ModuleResult, Status
from inspectlog.ui.widgets.confidence_badge import ConfidenceBadge
from inspectlog.ui.widgets.health_gauge import HealthGauge
from inspectlog.ui.widgets.tooltip_label import TooltipLabel, ValueDisplayWidget


class ModuleCard(QFrame):
    """Card widget rendering a single hardware module's results and health score."""

    def __init__(self, result: ModuleResult, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self._result = result
        self._expanded = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        # Header Row: Icon + Title + Score Gauge
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_label = QLabel(self._result.icon)
        icon_label.setStyleSheet("font-size: 26px;")
        header_layout.addWidget(icon_label)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_label = QLabel(self._result.display_name)
        title_label.setStyleSheet("font-size: 16px; font-weight: 700;")
        title_col.addWidget(title_label)

        duration_text = f"Scan duration: {round(self._result.test_duration, 2)}s" if self._result.test_duration > 0 else ""
        sub_label = QLabel(duration_text)
        sub_label.setObjectName("textMuted")
        title_col.addWidget(sub_label)
        header_layout.addLayout(title_col)

        header_layout.addStretch()

        # Circular Gauge
        self.gauge = HealthGauge(
            score=self._result.health_score,
            status=self._result.status,
            size=85,
        )
        header_layout.addWidget(self.gauge)
        main_layout.addLayout(header_layout)

        # Warning / Error Box if present
        if self._result.warnings or self._result.errors:
            alert_box = QFrame()
            alert_box.setObjectName("dangerCard" if self._result.errors else "highlightCard")
            alert_layout = QVBoxLayout(alert_box)
            alert_layout.setContentsMargins(10, 8, 10, 8)
            alert_layout.setSpacing(4)

            for err in self._result.errors:
                lbl = QLabel(f"❌ {err}")
                lbl.setStyleSheet("color: #ef4444; font-weight: 600;")
                lbl.setWordWrap(True)
                alert_layout.addWidget(lbl)

            for warn in self._result.warnings:
                lbl = QLabel(f"⚠️ {warn}")
                lbl.setStyleSheet("color: #f59e0b; font-weight: 500;")
                lbl.setWordWrap(True)
                alert_layout.addWidget(lbl)

            main_layout.addWidget(alert_box)

        # Readings Grid
        if self._result.readings:
            grid_widget = QWidget()
            grid = QGridLayout(grid_widget)
            grid.setContentsMargins(0, 4, 0, 4)
            grid.setHorizontalSpacing(14)
            grid.setVerticalSpacing(8)
            grid.setColumnStretch(1, 1)

            row = 0
            for key, verified in self._result.readings.items():
                # Format friendly label
                friendly_name = key.replace("_", " ").title()

                # Metric Title with info tooltip
                metric_lbl = TooltipLabel(key_name=key, display_title=friendly_name)
                grid.addWidget(metric_lbl, row, 0)

                # Value Display
                val_widget = ValueDisplayWidget(verified)
                grid.addWidget(val_widget, row, 1)

                # Confidence Badge
                badge = ConfidenceBadge(verified.confidence)
                grid.addWidget(badge, row, 2, Qt.AlignmentFlag.AlignRight)

                row += 1

            main_layout.addWidget(grid_widget)
        else:
            empty_msg = QLabel("Module was not tested or returned no readings.")
            empty_msg.setObjectName("textMuted")
            main_layout.addWidget(empty_msg)
