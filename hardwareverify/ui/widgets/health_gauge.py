"""Circular health score gauge widget."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from hardwareverify.core.models import Status


class HealthGauge(QWidget):
    """Visual circular gauge displaying a 0-100 score and status."""

    def __init__(
        self,
        score: int = 100,
        status: Status = Status.PASS,
        size: int = 110,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._score = score
        self._status = status
        self._size = size
        self.setFixedSize(size, size)

    def set_score(self, score: int, status: Status = Status.PASS) -> None:
        self._score = max(0, min(100, score))
        self._status = status
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        side = min(w, h)
        stroke_width = 8

        rect = QRectF(
            (w - side) / 2 + stroke_width / 2 + 4,
            (h - side) / 2 + stroke_width / 2 + 4,
            side - stroke_width - 8,
            side - stroke_width - 8,
        )

        # Background track arc (270 degrees)
        start_angle = 225 * 16
        span_angle = -270 * 16

        bg_pen = QPen(QColor("#2d3748"), stroke_width)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(rect, start_angle, span_angle)

        # Determine accent color based on score
        if self._score >= 80:
            color = QColor("#10b981")  # Emerald green
        elif self._score >= 50:
            color = QColor("#f59e0b")  # Amber
        else:
            color = QColor("#ef4444")  # Red

        if self._status == Status.NOT_TESTED:
            color = QColor("#64748b")  # Muted slate

        # Foreground score arc
        val_span = int((-270 * 16) * (self._score / 100.0))
        fg_pen = QPen(color, stroke_width)
        fg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(fg_pen)
        painter.drawArc(rect, start_angle, val_span)

        # Draw Center Score text
        painter.setPen(QColor("#f8fafc"))
        font = QFont("Segoe UI", 16, QFont.Weight.Bold)
        painter.setFont(font)

        if self._status == Status.NOT_TESTED:
            painter.drawText(
                QRectF(0, h * 0.28, w, 28),
                Qt.AlignmentFlag.AlignCenter,
                "—",
            )
        else:
            painter.drawText(
                QRectF(0, h * 0.28, w, 28),
                Qt.AlignmentFlag.AlignCenter,
                str(self._score),
            )

        # Draw Status Subtitle text
        sub_font = QFont("Segoe UI", 8, QFont.Weight.DemiBold)
        painter.setFont(sub_font)
        painter.setPen(color)
        status_text = self._status.value.upper()
        painter.drawText(
            QRectF(0, h * 0.58, w, 20),
            Qt.AlignmentFlag.AlignCenter,
            status_text,
        )
