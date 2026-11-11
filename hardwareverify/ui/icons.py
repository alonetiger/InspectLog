"""Flaticon icon set (see assets/icons/ATTRIBUTION.md) and the glass tiles they sit on."""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QLabel

from hardwareverify.constants import ASSETS_DIR

ICONS_DIR = os.path.join(ASSETS_DIR, "icons")

# Readers return numbered modules (storage_0, gpu_1, ...); map them to their base icon
_MODULE_PREFIXES = ("storage", "gpu", "display")


def icon_path(name: str) -> str:
    """Absolute path of an icon by name or module name; falls back to the generic computer icon."""
    for prefix in _MODULE_PREFIXES:
        if name.startswith(prefix):
            name = prefix
            break
    path = os.path.join(ICONS_DIR, f"{name}.png")
    return path if os.path.exists(path) else os.path.join(ICONS_DIR, "computer.png")


def icon(name: str) -> QIcon:
    return QIcon(icon_path(name))


def pixmap(name: str, size: int, device_pixel_ratio: float = 1.0) -> QPixmap:
    px = QPixmap(icon_path(name))
    if px.isNull():
        return px
    scaled = px.scaled(
        int(size * device_pixel_ratio),
        int(size * device_pixel_ratio),
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    scaled.setDevicePixelRatio(device_pixel_ratio)
    return scaled


def html_img(name: str, size: int = 14) -> str:
    """Inline <img> for rich-text labels."""
    path = icon_path(name).replace("\\", "/")
    return f'<img src="file:///{path}" width="{size}" height="{size}" style="vertical-align: middle;">'


class GlassIcon(QLabel):
    """An icon centred on a frosted, translucent rounded tile (styled as QLabel#glassIcon)."""

    def __init__(self, name: str, icon_size: int = 28, padding: int = 10, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("glassIcon")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(icon_size + padding * 2, icon_size + padding * 2)
        self._name = name
        self._icon_size = icon_size

    def showEvent(self, event) -> None:
        # Scale for the screen the tile is actually on so icons stay crisp at 125-200% scaling
        self.setPixmap(pixmap(self._name, self._icon_size, self.devicePixelRatioF()))
        super().showEvent(event)
