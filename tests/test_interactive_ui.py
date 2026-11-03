"""Unit tests for interactive UI test widgets."""

import sys
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QApplication

from hardwareverify.ui.interactive.display_test_window import (
    PATTERNS,
    DisplayTestResult,
    DisplayTestWindow,
)
from hardwareverify.ui.interactive.interactive_suite_dialog import InteractiveSuiteDialog
from hardwareverify.ui.interactive.keyboard_test_widget import KeyboardCanvas, KeyboardTestWidget
from hardwareverify.ui.interactive.mouse_test_widget import MouseCanvas, MouseGraphicWidget, MouseTestWidget


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def test_display_test_window(qapp):
    win = DisplayTestWindow()
    assert len(PATTERNS) == 7

    # Advance slides
    win._mark_pass()
    assert win.get_result().passed_slides == 1

    # Flag a defect
    win._flag_defect()
    assert len(win.get_result().defects) == 1
    assert not win.get_result().passed

    win._finish_test()
    assert win.get_result().completed


def test_keyboard_canvas(qapp):
    canvas = KeyboardCanvas()
    initial_total = canvas.total_unique_keys
    assert initial_total > 50

    # Simulate pressing 'A'
    press_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier)
    canvas.keyPressEvent(press_event)

    assert Qt.Key.Key_A in canvas.pressed_keys
    assert Qt.Key.Key_A in canvas.verified_keys

    # Simulate release
    rel_event = QKeyEvent(QKeyEvent.Type.KeyRelease, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier)
    canvas.keyReleaseEvent(rel_event)

    assert Qt.Key.Key_A not in canvas.pressed_keys
    assert Qt.Key.Key_A in canvas.verified_keys

    # Reset
    canvas.reset_test()
    assert len(canvas.verified_keys) == 0


def test_mouse_canvas(qapp):
    graphic = MouseGraphicWidget()
    canvas = MouseCanvas(graphic)

    # Simulate Left click (Qt6 non-deprecated signature: type, localPos, scenePos, button, buttons, modifiers)
    l_press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(100, 100),
        QPointF(100, 100),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(l_press)
    assert canvas.left_clicks == 1
    assert graphic.left_pressed

    # Simulate Right click
    r_press = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(100, 100),
        QPointF(100, 100),
        Qt.MouseButton.RightButton,
        Qt.MouseButton.RightButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(r_press)
    assert canvas.right_clicks == 1
    assert graphic.right_pressed

    # Simulate scroll wheel
    wheel = QWheelEvent(
        QPointF(100, 100),
        QPointF(100, 100),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    canvas.wheelEvent(wheel)
    assert canvas.scroll_up_count == 1


def test_interactive_suite_dialog(qapp):
    dialog = InteractiveSuiteDialog()
    assert dialog.tabs.count() == 7

    summary = dialog.collect_all_results()
    assert "display" in summary
    assert "keyboard" in summary
    assert "mouse" in summary
    assert "speakers" in summary
    assert "microphone" in summary
    assert "webcam" in summary
    assert "usb_ports" in summary
