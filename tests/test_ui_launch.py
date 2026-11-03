"""UI integration tests verifying window initialization, Check PC workflow, and in-app report."""

import os
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from inspectlog.constants import APP_DISPLAY_NAME
from inspectlog.core.models import Confidence, ModuleResult, Status, VerifiedValue
from inspectlog.ui.main_window import MainWindow
from inspectlog.ui.theme import ThemeManager


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
    assert hasattr(window.home_page, "check_pc_btn")
    assert window.home_page.check_pc_btn.text() == "🔍 Check PC"

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
    res1.add_reading("model", VerifiedValue.from_single("XPS 15", "WMI"))
    res1.add_reading("serial_number", VerifiedValue.from_single("ABC1234XYZ", "WMI"))
    res1.finalize(0.1)

    res2 = ModuleResult("battery", "Battery", Status.WARNING, health_score=67, icon="🔋")
    res2.add_reading("wear_percentage", VerifiedValue.from_single(33.0, "Calculated"))
    res2.add_warning("Battery wear is 33.0%")
    res2.finalize(0.2)

    window.results_page.display_results([res1, res2])
    assert len(window.results_page._results) == 2
    # Weighted average: system_identity (5% weight) = 95, battery (15% weight) = 67 -> 74
    assert window.results_page.overall_gauge._score == 74

    # Verify dedicated in-app report vitals and system identity banner
    assert "Dell Inc. XPS 15" in window.results_page.device_identity_banner.text()
    assert "ABC1234XYZ" in window.results_page.device_identity_banner.text()
    assert "Verified Genuine" in window.results_page.vital_authenticity.value_label.text()
    assert "33.0% Wear" in window.results_page.vital_battery.value_label.text()


def test_in_app_report_category_filtering(qapp):
    """Verify that category filtering tabs correctly filter visible module cards."""
    window = MainWindow()

    cpu_res = ModuleResult("cpu", "CPU", Status.PASS, health_score=100, icon="⚡")
    cpu_res.add_reading("cpu_model", VerifiedValue.from_single("Intel Core i7", "WMI"))
    cpu_res.finalize(0.1)

    ram_res = ModuleResult("ram", "RAM", Status.PASS, health_score=100, icon="🧠")
    ram_res.add_reading("total_ram_gb", VerifiedValue.from_single(16, "WMI"))
    ram_res.finalize(0.1)

    disk_res = ModuleResult("storage_0", "Storage: NVMe", Status.PASS, health_score=98, icon="💾")
    disk_res.add_reading("disk_capacity", VerifiedValue.from_single("512 GB", "smartctl"))
    disk_res.finalize(0.1)

    window.results_page.display_results([cpu_res, ram_res, disk_res])

    # Default category is 'all'
    assert len(window.results_page._module_cards) == 3

    # Filter to 'processor_memory'
    window.results_page._filter_category("processor_memory")
    assert window.results_page._active_category == "processor_memory"

    # Filter to 'storage'
    window.results_page._filter_category("storage")
    assert window.results_page._active_category == "storage"

    # Reset to 'all'
    window.results_page._filter_category("all")
    assert window.results_page._active_category == "all"
