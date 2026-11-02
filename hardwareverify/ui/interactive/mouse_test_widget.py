"""Interactive Mouse and Touchpad diagnostic widget."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QMouseEvent,
    QPainter,
    QPen,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hardwareverify.infra.logging import get_logger

logger = get_logger("mouse_test_widget")


class MouseGraphicWidget(QWidget):
    """Visual diagram of a mouse highlighting pressed buttons."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(140, 200)

        self.left_pressed = False
        self.right_pressed = False
        self.middle_pressed = False

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Mouse body outline
        body_rect = QRectF(10, 10, 120, 180)
        painter.setPen(QPen(QColor(51, 65, 85), 2))
        painter.setBrush(QColor(15, 23, 42))
        painter.drawRoundedRect(body_rect, 60, 60)

        # Left button top area
        left_color = QColor(16, 185, 129) if self.left_pressed else QColor(30, 41, 59)
        painter.setBrush(left_color)
        painter.drawRoundedRect(QRectF(15, 15, 50, 60), 20, 20)

        # Right button top area
        right_color = QColor(16, 185, 129) if self.right_pressed else QColor(30, 41, 59)
        painter.setBrush(right_color)
        painter.drawRoundedRect(QRectF(75, 15, 50, 60), 20, 20)

        # Middle scroll wheel
        mid_color = QColor(56, 189, 248) if self.middle_pressed else QColor(71, 85, 105)
        painter.setBrush(mid_color)
        painter.drawRoundedRect(QRectF(60, 25, 20, 40), 10, 10)

        # Labels
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.setPen(QColor(255, 255, 255) if self.left_pressed else QColor(148, 163, 184))
        painter.drawText(QRectF(15, 30, 50, 30), Qt.AlignmentFlag.AlignCenter, "L")

        painter.setPen(QColor(255, 255, 255) if self.right_pressed else QColor(148, 163, 184))
        painter.drawText(QRectF(75, 30, 50, 30), Qt.AlignmentFlag.AlignCenter, "R")

        painter.setPen(QColor(255, 255, 255) if self.middle_pressed else QColor(203, 213, 225))
        painter.drawText(QRectF(60, 32, 20, 25), Qt.AlignmentFlag.AlignCenter, "M")

        painter.end()


class MouseCanvas(QFrame):
    """Drawing and gesture testing area for tracking cursor smoothness and clicks."""

    def __init__(self, graphic: MouseGraphicWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.graphic = graphic
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(450, 240)
        self.setMouseTracking(True)
        self.setStyleSheet("""
            QFrame {
                background-color: #0F172A;
                border: 2px dashed #334155;
                border-radius: 8px;
            }
        """)

        self.paths: list[list[QPoint]] = []
        self.current_path: list[QPoint] = []

        # Counts
        self.left_clicks = 0
        self.right_clicks = 0
        self.middle_clicks = 0
        self.double_clicks = 0
        self.scroll_up_count = 0
        self.scroll_down_count = 0

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.left_clicks += 1
            self.graphic.left_pressed = True
            self.current_path = [event.pos()]
            self.paths.append(self.current_path)
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicks += 1
            self.graphic.right_pressed = True
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.middle_clicks += 1
            self.graphic.middle_pressed = True

        self.graphic.update()
        self.update()
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.graphic.left_pressed = False
        elif event.button() == Qt.MouseButton.RightButton:
            self.graphic.right_pressed = False
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.graphic.middle_pressed = False

        self.graphic.update()
        self.update()
        event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self.double_clicks += 1
        self.update()
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            if self.current_path:
                self.current_path.append(event.pos())
                self.update()
        event.accept()

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta > 0:
            self.scroll_up_count += 1
        elif delta < 0:
            self.scroll_down_count += 1
        self.graphic.middle_pressed = True
        self.graphic.update()
        self.update()
        event.accept()

    def clear_canvas(self) -> None:
        self.paths.clear()
        self.current_path.clear()
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Draw paths
        pen = QPen(QColor(56, 189, 248), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        for path in self.paths:
            for i in range(len(path) - 1):
                painter.drawLine(path[i], path[i + 1])

        # If canvas is empty, draw guidance watermark
        if not self.paths:
            painter.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
            painter.setPen(QColor(71, 85, 105))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Click and drag here to verify cursor smoothness & gestures\nRight click, Middle click, and Scroll to verify buttons",
            )

        painter.end()


class MouseTestWidget(QWidget):
    """Complete Mouse and Touchpad test tab."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        header_row = QHBoxLayout()
        lbl_title = QLabel("Mouse & Touchpad Diagnostic")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #E2E8F0;")
        header_row.addWidget(lbl_title)
        header_row.addStretch()
        layout.addLayout(header_row)

        desc = QLabel(
            "Test Left, Right, and Middle clicks, double-click responsiveness, scroll wheel, "
            "and drag the cursor across the canvas to verify touchpad tracking linearity."
        )
        desc.setStyleSheet("color: #94A3B8; font-size: 13px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Main work area: Graphic + Canvas
        work_area = QHBoxLayout()
        self.graphic = MouseGraphicWidget(self)
        work_area.addWidget(self.graphic, alignment=Qt.AlignmentFlag.AlignTop)

        self.canvas = MouseCanvas(self.graphic, self)
        work_area.addWidget(self.canvas, 1)

        layout.addLayout(work_area)

        # Stats badges row
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: #1E293B;
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                font-family: 'Segoe UI', system-ui;
                font-size: 12px;
                color: #CBD5E1;
            }
            b { color: #38BDF8; }
        """)
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setSpacing(20)

        self.lbl_l_clicks = QLabel("Left: <b>0</b>")
        self.lbl_r_clicks = QLabel("Right: <b>0</b>")
        self.lbl_m_clicks = QLabel("Middle: <b>0</b>")
        self.lbl_dbl_clicks = QLabel("Double: <b>0</b>")
        self.lbl_scroll = QLabel("Scroll: <b>0</b>")

        stats_layout.addWidget(self.lbl_l_clicks)
        stats_layout.addWidget(self.lbl_r_clicks)
        stats_layout.addWidget(self.lbl_m_clicks)
        stats_layout.addWidget(self.lbl_dbl_clicks)
        stats_layout.addWidget(self.lbl_scroll)
        stats_layout.addStretch()

        self.btn_clear = QPushButton("Clear Canvas")
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #E2E8F0;
                font-weight: 600;
                padding: 4px 12px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        self.btn_clear.clicked.connect(self.canvas.clear_canvas)
        stats_layout.addWidget(self.btn_clear)

        layout.addWidget(stats_frame)

        # Update stats timer or repaint hook
        self.canvas.mousePressEvent = self._wrap_canvas_press(self.canvas.mousePressEvent)
        self.canvas.wheelEvent = self._wrap_canvas_wheel(self.canvas.wheelEvent)

    def _wrap_canvas_press(self, orig_func):
        def wrapper(event):
            orig_func(event)
            self._update_stats()
        return wrapper

    def _wrap_canvas_wheel(self, orig_func):
        def wrapper(event):
            orig_func(event)
            self._update_stats()
        return wrapper

    def _update_stats(self) -> None:
        self.lbl_l_clicks.setText(f"Left: <b>{self.canvas.left_clicks}</b>")
        self.lbl_r_clicks.setText(f"Right: <b>{self.canvas.right_clicks}</b>")
        self.lbl_m_clicks.setText(f"Middle: <b>{self.canvas.middle_clicks}</b>")
        self.lbl_dbl_clicks.setText(f"Double: <b>{self.canvas.double_clicks}</b>")
        total_scroll = self.canvas.scroll_up_count + self.canvas.scroll_down_count
        self.lbl_scroll.setText(f"Scroll: <b>{total_scroll}</b>")

    def get_test_summary(self) -> dict[str, Any]:
        """Return verification outcome for report generation."""
        has_left = self.canvas.left_clicks > 0
        has_right = self.canvas.right_clicks > 0
        has_scroll = (self.canvas.scroll_up_count + self.canvas.scroll_down_count) > 0
        passed = has_left and has_right

        return {
            "left_clicks": self.canvas.left_clicks,
            "right_clicks": self.canvas.right_clicks,
            "middle_clicks": self.canvas.middle_clicks,
            "scroll_events": self.canvas.scroll_up_count + self.canvas.scroll_down_count,
            "passed": passed,
        }
