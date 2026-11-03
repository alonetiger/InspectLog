"""Application bootstrap and lifecycle management."""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from hardwareverify.constants import APP_DISPLAY_NAME, APP_NAME
from hardwareverify.infra.logging import get_logger, setup_logging
from hardwareverify.ui.main_window import MainWindow
from hardwareverify.ui.theme import ThemeManager

logger = get_logger("app")


def create_app() -> tuple[QApplication, MainWindow]:
    """Initialize and configure the Qt Application and Main Window."""
    # Enable high-DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)

    # Apply default dark theme
    ThemeManager.apply_theme(app, "dark")

    window = MainWindow()
    return app, window


def run() -> int:
    """Main execution loop."""
    setup_logging()
    logger.info("%s starting up...", APP_DISPLAY_NAME)

    app, window = create_app()
    window.show()

    exit_code = app.exec()
    logger.info("%s exiting with code %d", APP_DISPLAY_NAME, exit_code)
    return exit_code
