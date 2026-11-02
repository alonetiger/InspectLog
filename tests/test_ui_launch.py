"""UI integration tests verifying window initialization and page transitions."""

import os
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from hardwareverify.constants import APP_DISPLAY_NAME
from hardwareverify.core.models import Confidence, ModuleResult, Status, VerifiedValue
from hardwareverify.ui.main_window import MainWindow
from hardwareverify.ui.theme import ThemeManager


@pytest.fixture(scope="session")
def qapp():
    """Ensure a single QApplication instance exists for tests."""
    app = QApplication.instance()
    if app is None:
        # Enable offscreen rendering for headless CI / environments
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        app = QApplication([])
    return app


def test_main_window_init(qapp):
    ThemeManager.apply_theme(qapp, "dark")
    window = MainWindow()
    assert window.windowTitle().startswith(APP_DISPLAY_NAME)

    # Should start on Page 0 (Home Page)
    assert window.stacked_widget.currentIndex() == 0

    # Test Theme Toggle
    ThemeManager.apply_theme(qapp, "light")
    assert ThemeManager.current_theme() == "light"
    ThemeManager.apply_theme(qapp, "dark")
    assert ThemeManager.current_theme() == "dark"


def test_results_page_display(qapp):
    window = MainWindow()

    # Create dummy results
    res1 = ModuleResult("system_identity", "System Identity", Status.PASS, health_score=95, icon="🖥️")
    res1.add_reading("manufacturer", VerifiedValue.from_single("Dell Inc.", "WMI"))
    res1.finalize(0.1)

    res2 = ModuleResult("battery", "Battery", Status.WARNING, health_score=67, icon="🔋")
    res2.add_reading("wear_percentage", VerifiedValue.from_single(33.0, "Calculated"))
    res2.add_warning("Battery wear is 33.0%")
    res2.finalize(0.2)

    window.results_page.display_results([res1, res2])
    assert len(window.results_page._results) == 2
    # Weighted average: system_identity (5% weight) = 95, battery (15% weight) = 67 -> 74
    assert window.results_page.overall_gauge._score == 74
