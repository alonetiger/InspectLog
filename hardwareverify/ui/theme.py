"""UI theme definitions and manager for the "Glass Transparent" theme, in dark and light variants.

Qt stylesheets cannot blur what is behind a widget, so the glass look is built in two layers:
an aurora backdrop painted by ``GlassBackdrop`` behind every page, and translucent cards with
a light rim and a top-to-bottom sheen drawn by the stylesheet on top of it.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QRadialGradient
from PySide6.QtWidgets import QApplication, QWidget

COLORS_DARK = {
    # Backdrop: deep navy base with violet, cyan and pink aurora glows
    "bg_main": "#070b1a",
    "bg_main_end": "#0c1230",
    "glow_1": "#7c3aed",
    "glow_2": "#06b6d4",
    "glow_3": "#ec4899",
    "glow_alpha": "0.42",
    # Glass surfaces
    "bg_card": "rgba(255, 255, 255, 0.07)",
    "bg_card_top": "rgba(255, 255, 255, 0.11)",
    "bg_card_bottom": "rgba(255, 255, 255, 0.04)",
    "bg_card_alt": "rgba(255, 255, 255, 0.08)",
    "bg_card_hover": "rgba(255, 255, 255, 0.14)",
    "bg_sunken": "rgba(3, 6, 20, 0.45)",
    "bg_dialog": "#0d1330",
    "bg_dialog_end": "#141a3d",
    "bg_popup": "#151b3f",
    "border_subtle": "rgba(255, 255, 255, 0.12)",
    "border_strong": "rgba(255, 255, 255, 0.24)",
    "border_glow": "rgba(167, 139, 250, 0.55)",
    # Accents
    "accent_primary": "#8b5cf6",
    "accent_primary_end": "#06b6d4",
    "accent_primary_hover": "#7c3aed",
    "accent_primary_hover_end": "#0891b2",
    "accent_success": "#34d399",
    "accent_warning": "#fbbf24",
    "accent_danger": "#f87171",
    "accent_info": "#38bdf8",
    "tint_success": "rgba(52, 211, 153, 0.14)",
    "tint_warning": "rgba(251, 191, 36, 0.14)",
    "tint_danger": "rgba(248, 113, 113, 0.14)",
    "tint_info": "rgba(56, 189, 248, 0.14)",
    "rim_success": "rgba(52, 211, 153, 0.40)",
    "rim_warning": "rgba(251, 191, 36, 0.40)",
    "rim_danger": "rgba(248, 113, 113, 0.45)",
    # Text
    "text_primary": "#f5f7ff",
    "text_secondary": "#aab4d4",
    "text_muted": "#6f7aa0",
    "text_on_accent": "#ffffff",
    "gauge_bg": "#26ffffff",
}

COLORS_LIGHT = {
    "bg_main": "#eef1ff",
    "bg_main_end": "#f8f9ff",
    "glow_1": "#a78bfa",
    "glow_2": "#22d3ee",
    "glow_3": "#f472b6",
    "glow_alpha": "0.38",
    "bg_card": "rgba(255, 255, 255, 0.55)",
    "bg_card_top": "rgba(255, 255, 255, 0.78)",
    "bg_card_bottom": "rgba(255, 255, 255, 0.48)",
    "bg_card_alt": "rgba(255, 255, 255, 0.62)",
    "bg_card_hover": "rgba(255, 255, 255, 0.85)",
    "bg_sunken": "rgba(15, 23, 42, 0.05)",
    "bg_dialog": "#f3f4ff",
    "bg_dialog_end": "#fbfbff",
    "bg_popup": "#ffffff",
    "border_subtle": "rgba(15, 23, 42, 0.09)",
    "border_strong": "rgba(15, 23, 42, 0.18)",
    "border_glow": "rgba(124, 58, 237, 0.45)",
    "accent_primary": "#7c3aed",
    "accent_primary_end": "#0891b2",
    "accent_primary_hover": "#6d28d9",
    "accent_primary_hover_end": "#0e7490",
    "accent_success": "#059669",
    "accent_warning": "#b45309",
    "accent_danger": "#dc2626",
    "accent_info": "#0284c7",
    "tint_success": "rgba(5, 150, 105, 0.10)",
    "tint_warning": "rgba(217, 119, 6, 0.10)",
    "tint_danger": "rgba(220, 38, 38, 0.09)",
    "tint_info": "rgba(2, 132, 199, 0.10)",
    "rim_success": "rgba(5, 150, 105, 0.35)",
    "rim_warning": "rgba(217, 119, 6, 0.35)",
    "rim_danger": "rgba(220, 38, 38, 0.35)",
    "text_primary": "#0f172a",
    "text_secondary": "#475569",
    "text_muted": "#8a94ad",
    "text_on_accent": "#ffffff",
    "gauge_bg": "#1a0f172a",
}


def build_stylesheet(colors: dict[str, str]) -> str:
    """Generate Qt stylesheet for given color mapping."""
    c = colors
    glass = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {c['bg_card_top']}, stop:1 {c['bg_card_bottom']})"
    accent = f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {c['accent_primary']}, stop:1 {c['accent_primary_end']})"
    accent_hover = (
        f"qlineargradient(x1:0, y1:0, x2:1, y2:0, "
        f"stop:0 {c['accent_primary_hover']}, stop:1 {c['accent_primary_hover_end']})"
    )
    dialog_bg = f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {c['bg_dialog']}, stop:1 {c['bg_dialog_end']})"

    return f"""
    QMainWindow {{
        background-color: {c["bg_main"]};
    }}

    QWidget {{
        color: {c["text_primary"]};
        font-family: 'Segoe UI Variable Text', 'Segoe UI', system-ui, sans-serif;
        font-size: 13px;
    }}

    QDialog, QMessageBox {{
        background: {dialog_bg};
    }}

    /* ---------- Glass surfaces ---------- */

    QFrame#cardFrame, QFrame#heroCard {{
        background: {glass};
        border: 1px solid {c["border_subtle"]};
        border-radius: 18px;
    }}

    QFrame#cardFrame:hover {{
        border: 1px solid {c["border_strong"]};
    }}

    QFrame#heroCard {{
        border: 1px solid {c["border_glow"]};
        border-radius: 22px;
    }}

    QFrame#sunkenPanel, QFrame#vitalBadge {{
        background-color: {c["bg_sunken"]};
        border: 1px solid {c["border_subtle"]};
        border-radius: 12px;
    }}

    QFrame#highlightCard, QFrame#warningCard {{
        background-color: {c["tint_warning"]};
        border: 1px solid {c["rim_warning"]};
        border-radius: 12px;
    }}

    QFrame#dangerCard {{
        background-color: {c["tint_danger"]};
        border: 1px solid {c["rim_danger"]};
        border-radius: 12px;
    }}

    QFrame#successCard {{
        background-color: {c["tint_success"]};
        border: 1px solid {c["rim_success"]};
        border-radius: 12px;
    }}

    /* ---------- Buttons ---------- */

    QPushButton {{
        background: {accent};
        color: {c["text_on_accent"]};
        border: 1px solid rgba(255, 255, 255, 0.18);
        border-radius: 10px;
        padding: 9px 18px;
        font-weight: 600;
    }}

    QPushButton:hover {{
        background: {accent_hover};
        border: 1px solid rgba(255, 255, 255, 0.30);
    }}

    QPushButton:disabled {{
        background: {c["bg_card_alt"]};
        color: {c["text_muted"]};
        border: 1px solid {c["border_subtle"]};
    }}

    QPushButton#heroButton {{
        font-size: 17px;
        font-weight: 700;
        border-radius: 14px;
        padding: 12px 40px;
    }}

    QPushButton#secondaryButton, QPushButton#filterChip {{
        background: {c["bg_card_alt"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border_subtle"]};
    }}

    QPushButton#secondaryButton:hover, QPushButton#filterChip:hover:!checked {{
        background: {c["bg_card_hover"]};
        border: 1px solid {c["border_strong"]};
    }}

    QPushButton#secondaryButton::menu-indicator {{
        subcontrol-position: right center;
        right: 8px;
    }}

    QPushButton#filterChip {{
        color: {c["text_secondary"]};
        border-radius: 15px;
        padding: 6px 14px;
        font-size: 12px;
    }}

    QPushButton#filterChip:checked {{
        background: {accent};
        color: {c["text_on_accent"]};
        border: 1px solid rgba(255, 255, 255, 0.25);
    }}

    QPushButton#dangerButton {{
        background: {c["tint_danger"]};
        color: {c["accent_danger"]};
        border: 1px solid {c["rim_danger"]};
    }}

    QPushButton#dangerButton:hover {{
        background: {c["accent_danger"]};
        color: {c["text_on_accent"]};
    }}

    /* ---------- Text ---------- */

    QLabel {{
        background: transparent;
        color: {c["text_primary"]};
    }}

    QLabel#textMuted {{
        color: {c["text_muted"]};
        font-size: 12px;
    }}

    QLabel#textSecondary, QLabel#pageSubtitle, QLabel#cardBody {{
        color: {c["text_secondary"]};
    }}

    QLabel#pageTitle {{
        font-size: 26px;
        font-weight: 800;
    }}

    QLabel#pageSubtitle {{
        font-size: 13px;
    }}

    QLabel#heroTitle {{
        font-size: 22px;
        font-weight: 800;
    }}

    QLabel#cardTitle {{
        font-size: 16px;
        font-weight: 700;
    }}

    QLabel#cardBody {{
        font-size: 12px;
    }}

    QLabel#glassIcon {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 {c["bg_card_hover"]}, stop:1 {c["bg_card_bottom"]});
        border: 1px solid {c["border_strong"]};
        border-radius: 14px;
    }}

    QLabel#vitalTitle {{
        color: {c["text_muted"]};
        font-size: 11px;
        font-weight: 600;
    }}

    QLabel#pill {{
        background-color: {c["bg_card_alt"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border_subtle"]};
        border-radius: 12px;
        padding: 5px 12px;
        font-size: 11px;
        font-weight: 600;
    }}

    QLabel#identityPill {{
        background-color: {c["bg_sunken"]};
        color: {c["accent_info"]};
        border: 1px solid {c["border_subtle"]};
        border-radius: 10px;
        padding: 6px 12px;
        font-size: 12px;
        font-weight: 600;
    }}

    QLabel#badgeSuccess, QLabel#badgeWarning, QLabel#badgeDanger {{
        border-radius: 10px;
        padding: 6px 14px;
        font-size: 12px;
        font-weight: 600;
    }}

    QLabel#badgeSuccess {{
        background-color: {c["tint_success"]};
        color: {c["accent_success"]};
        border: 1px solid {c["rim_success"]};
    }}

    QLabel#badgeWarning {{
        background-color: {c["tint_warning"]};
        color: {c["accent_warning"]};
        border: 1px solid {c["rim_warning"]};
    }}

    QLabel#badgeDanger {{
        background-color: {c["tint_danger"]};
        color: {c["accent_danger"]};
        border: 1px solid {c["rim_danger"]};
    }}

    QLabel#successText {{
        color: {c["accent_success"]};
    }}

    QLabel#warningText {{
        color: {c["accent_warning"]};
    }}

    QLabel#dangerText {{
        color: {c["accent_danger"]};
    }}

    QLabel#infoText {{
        color: {c["accent_info"]};
    }}

    /* ---------- Inputs ---------- */

    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
        background-color: {c["bg_sunken"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border_subtle"]};
        border-radius: 8px;
        padding: 6px 10px;
        selection-background-color: {c["accent_primary"]};
    }}

    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
        border: 1px solid {c["border_glow"]};
    }}

    QComboBox QAbstractItemView {{
        background-color: {c["bg_popup"]};
        border: 1px solid {c["border_strong"]};
        selection-background-color: {c["accent_primary"]};
    }}

    QProgressBar {{
        background-color: {c["bg_sunken"]};
        border: 1px solid {c["border_subtle"]};
        border-radius: 8px;
        text-align: center;
        color: {c["text_primary"]};
        font-weight: 600;
        min-height: 16px;
    }}

    QProgressBar::chunk {{
        background: {accent};
        border-radius: 7px;
    }}

    /* ---------- Tables, menus, tabs ---------- */

    QTableWidget {{
        background-color: {c["bg_sunken"]};
        alternate-background-color: {c["bg_card"]};
        border: 1px solid {c["border_subtle"]};
        border-radius: 10px;
        gridline-color: {c["border_subtle"]};
        font-size: 12px;
    }}

    QHeaderView::section {{
        background-color: {c["bg_card_alt"]};
        color: {c["text_secondary"]};
        font-weight: 600;
        padding: 6px;
        border: none;
    }}

    QTableCornerButton::section {{
        background-color: {c["bg_card_alt"]};
        border: none;
    }}

    QMenu {{
        background-color: {c["bg_popup"]};
        border: 1px solid {c["border_strong"]};
        border-radius: 10px;
        padding: 6px;
    }}

    QMenu::item {{
        padding: 7px 18px;
        border-radius: 6px;
    }}

    QMenu::item:selected {{
        background-color: {c["bg_card_hover"]};
    }}

    QTabWidget::pane {{
        background: {glass};
        border: 1px solid {c["border_subtle"]};
        border-radius: 14px;
    }}

    QTabBar::tab {{
        background: transparent;
        color: {c["text_secondary"]};
        padding: 9px 16px;
        margin-right: 4px;
        border-radius: 10px;
        font-weight: 600;
    }}

    QTabBar::tab:selected {{
        background: {c["bg_card_hover"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border_subtle"]};
    }}

    QTabBar::tab:hover:!selected {{
        background: {c["bg_card_alt"]};
    }}

    /* ---------- Scrolling ---------- */

    QScrollArea, QScrollArea > QWidget > QWidget {{
        border: none;
        background: transparent;
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 2px;
    }}

    QScrollBar::handle:vertical {{
        background: {c["border_strong"]};
        min-height: 28px;
        border-radius: 3px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {c["text_muted"]};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        height: 0px;
        background: transparent;
    }}

    QToolTip {{
        background-color: {c["bg_popup"]};
        color: {c["text_primary"]};
        border: 1px solid {c["border_strong"]};
        border-radius: 8px;
        padding: 6px 10px;
        font-size: 12px;
    }}
    """


class GlassBackdrop(QWidget):
    """Paints the aurora gradient that the translucent glass cards sit on."""

    def paintEvent(self, event) -> None:
        colors = ThemeManager.get_colors()
        w, h = self.width(), self.height()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        base = QLinearGradient(0, 0, w, h)
        base.setColorAt(0.0, QColor(colors["bg_main"]))
        base.setColorAt(1.0, QColor(colors["bg_main_end"]))
        painter.fillRect(self.rect(), base)

        alpha = float(colors["glow_alpha"])
        span = max(w, h)
        glows = [
            (colors["glow_1"], QPointF(w * 0.12, h * 0.05), span * 0.55, alpha),
            (colors["glow_2"], QPointF(w * 0.95, h * 0.35), span * 0.50, alpha * 0.8),
            (colors["glow_3"], QPointF(w * 0.40, h * 1.05), span * 0.55, alpha * 0.6),
        ]
        painter.setPen(Qt.PenStyle.NoPen)
        for hex_color, center, radius, strength in glows:
            glow = QRadialGradient(center, radius)
            inner = QColor(hex_color)
            inner.setAlphaF(strength)
            outer = QColor(hex_color)
            outer.setAlphaF(0.0)
            glow.setColorAt(0.0, inner)
            glow.setColorAt(1.0, outer)
            painter.setBrush(glow)
            painter.drawRect(self.rect())


def apply_window_chrome(widget: QWidget, dark: bool) -> None:
    """Match the native Windows 11 title bar to the active theme (no-op elsewhere)."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = int(widget.winId())
        value = ctypes.c_int(1 if dark else 0)
        # DWMWA_USE_IMMERSIVE_DARK_MODE
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(value), ctypes.sizeof(value))
        # DWMWA_WINDOW_CORNER_PREFERENCE = DWMWCP_ROUND
        corner = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner), ctypes.sizeof(corner))
    except (AttributeError, OSError):
        pass


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
        for window in app.topLevelWidgets():
            if window.isWindow() and window.isVisible():
                apply_window_chrome(window, theme_name == "dark")
            window.update()
