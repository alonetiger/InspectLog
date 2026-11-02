"""UI Theme definitions and manager for Dark and Light themes."""

from __future__ import annotations

from typing import Any
from PySide6.QtWidgets import QApplication

COLORS_DARK = {
    "bg_main": "#121824",
    "bg_card": "#1a2234",
    "bg_card_alt": "#212b40",
    "bg_card_hover": "#26324b",
    "accent_primary": "#3b82f6",
    "accent_primary_hover": "#2563eb",
    "accent_success": "#10b981",
    "accent_warning": "#f59e0b",
    "accent_danger": "#ef4444",
    "accent_info": "#06b6d4",
    "text_primary": "#f8fafc",
    "text_secondary": "#94a3b8",
    "text_muted": "#64748b",
    "border_subtle": "#2e3a52",
    "border_strong": "#3e4c6d",
    "gauge_bg": "#222c42",
}

COLORS_LIGHT = {
    "bg_main": "#f8fafc",
    "bg_card": "#ffffff",
    "bg_card_alt": "#f1f5f9",
    "bg_card_hover": "#e2e8f0",
    "accent_primary": "#2563eb",
    "accent_primary_hover": "#1d4ed8",
    "accent_success": "#059669",
    "accent_warning": "#d97706",
    "accent_danger": "#dc2626",
    "accent_info": "#0891b2",
    "text_primary": "#0f172a",
    "text_secondary": "#475569",
    "text_muted": "#94a3b8",
    "border_subtle": "#e2e8f0",
    "border_strong": "#cbd5e1",
    "gauge_bg": "#e2e8f0",
}


def build_stylesheet(colors: dict[str, str]) -> str:
    """Generate Qt stylesheet for given color mapping."""
    return f"""
    QMainWindow, QWidget#centralWidget {{
        background-color: {colors["bg_main"]};
        color: {colors["text_primary"]};
        font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
        font-size: 13px;
    }}

    QWidget {{
        color: {colors["text_primary"]};
    }}

    QFrame#cardFrame {{
        background-color: {colors["bg_card"]};
        border: 1px solid {colors["border_subtle"]};
        border-radius: 12px;
    }}

    QFrame#cardFrame:hover {{
        border: 1px solid {colors["border_strong"]};
    }}

    QFrame#highlightCard {{
        background-color: {colors["bg_card"]};
        border: 2px solid {colors["accent_primary"]};
        border-radius: 12px;
    }}

    QFrame#dangerCard {{
        background-color: {colors["bg_card"]};
        border: 2px solid {colors["accent_danger"]};
        border-radius: 12px;
    }}

    QPushButton {{
        background-color: {colors["accent_primary"]};
        color: #ffffff;
        border: none;
        border-radius: 8px;
        padding: 10px 18px;
        font-weight: 600;
        font-size: 13px;
    }}

    QPushButton:hover {{
        background-color: {colors["accent_primary_hover"]};
    }}

    QPushButton:pressed {{
        opacity: 0.85;
    }}

    QPushButton#secondaryButton {{
        background-color: {colors["bg_card_alt"]};
        color: {colors["text_primary"]};
        border: 1px solid {colors["border_subtle"]};
    }}

    QPushButton#secondaryButton:hover {{
        background-color: {colors["bg_card_hover"]};
        border-color: {colors["border_strong"]};
    }}

    QPushButton#dangerButton {{
        background-color: {colors["accent_danger"]};
        color: #ffffff;
    }}

    QPushButton#dangerButton:hover {{
        background-color: #b91c1c;
    }}

    QLabel {{
        color: {colors["text_primary"]};
    }}

    QLabel#textMuted {{
        color: {colors["text_muted"]};
        font-size: 12px;
    }}

    QLabel#textSecondary {{
        color: {colors["text_secondary"]};
    }}

    QLabel#pageTitle {{
        font-size: 24px;
        font-weight: 700;
        color: {colors["text_primary"]};
    }}

    QLabel#pageSubtitle {{
        font-size: 14px;
        color: {colors["text_secondary"]};
    }}

    QProgressBar {{
        background-color: {colors["bg_card_alt"]};
        border: 1px solid {colors["border_subtle"]};
        border-radius: 6px;
        text-align: center;
        color: {colors["text_primary"]};
        font-weight: 600;
        height: 14px;
    }}

    QProgressBar::chunk {{
        background-color: {colors["accent_primary"]};
        border-radius: 5px;
    }}

    QScrollArea {{
        border: none;
        background-color: transparent;
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0px;
    }}

    QScrollBar::handle:vertical {{
        background: {colors["border_strong"]};
        min-height: 24px;
        border-radius: 4px;
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QToolTip {{
        background-color: {colors["bg_card"]};
        color: {colors["text_primary"]};
        border: 1px solid {colors["border_strong"]};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
    }}
    """


class ThemeManager:
    """Manages active theme application and persistence."""

    _current_theme: str = "dark"

    @classmethod
    def current_theme(cls) -> str:
        return cls._current_theme

    @classmethod
    def get_colors(cls) -> dict[str, str]:
        return COLORS_DARK if cls._current_theme == "dark" else COLORS_LIGHT

    @classmethod
    def apply_theme(cls, app: QApplication, theme_name: str = "dark") -> None:
        cls._current_theme = theme_name
        colors = cls.get_colors()
        qss = build_stylesheet(colors)
        app.setStyleSheet(qss)
