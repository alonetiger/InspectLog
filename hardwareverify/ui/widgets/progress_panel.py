"""Scan progress panel displaying module-by-module execution status."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class ModuleProgressItem(QFrame):
    """Row displaying the state of a single module during a scan."""

    def __init__(self, module_name: str, display_name: str, icon: str = "🔍", parent=None) -> None:
        super().__init__(parent)
        self.module_name = module_name
        self.setObjectName("cardFrame")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        self.icon_lbl = QLabel(icon)
        self.icon_lbl.setStyleSheet("font-size: 18px;")
        layout.addWidget(self.icon_lbl)

        self.name_lbl = QLabel(display_name)
        self.name_lbl.setStyleSheet("font-weight: 600;")
        layout.addWidget(self.name_lbl)

        layout.addStretch()

        self.status_lbl = QLabel("Pending")
        self.status_lbl.setObjectName("textMuted")
        layout.addWidget(self.status_lbl)

    def set_status(self, status: str, detail: str | None = None) -> None:
        if status == "running":
            self.status_lbl.setText("🔄 Running...")
            self.status_lbl.setStyleSheet("color: #3b82f6; font-weight: 600;")
        elif status == "completed":
            self.status_lbl.setText("✅ Completed")
            self.status_lbl.setStyleSheet("color: #10b981; font-weight: 600;")
        elif status == "warning":
            self.status_lbl.setText("⚠️ Warning")
            self.status_lbl.setStyleSheet("color: #f59e0b; font-weight: 600;")
        elif status == "failed":
            self.status_lbl.setText("❌ Failed")
            self.status_lbl.setStyleSheet("color: #ef4444; font-weight: 600;")
        else:
            self.status_lbl.setText("⏳ Pending")
            self.status_lbl.setStyleSheet("color: #64748b;")


class ProgressPanel(QWidget):
    """Panel with overall progress bar and list of all module tasks."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._items: dict[str, ModuleProgressItem] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Module list container
        self.list_container = QVBoxLayout()
        self.list_container.setSpacing(8)
        layout.addLayout(self.list_container)

    def set_modules(self, modules: list[tuple[str, str, str]]) -> None:
        """Initialize the list with (module_name, display_name, icon) tuples."""
        # Clear existing
        for item in self._items.values():
            item.setParent(None)
        self._items.clear()

        for mod_name, disp_name, icon in modules:
            item = ModuleProgressItem(mod_name, disp_name, icon)
            self._items[mod_name] = item
            self.list_container.addWidget(item)

    def set_module_running(self, module_name: str) -> None:
        target = module_name
        if target not in self._items:
            for k in self._items:
                if module_name.startswith(k):
                    target = k
                    break
        if target in self._items:
            self._items[target].set_status("running")

    def set_module_completed(self, module_name: str, has_warnings: bool = False, has_errors: bool = False) -> None:
        target = module_name
        if target not in self._items:
            for k in self._items:
                if module_name.startswith(k):
                    target = k
                    break
        if target in self._items:
            if has_errors:
                self._items[target].set_status("failed")
            elif has_warnings:
                self._items[target].set_status("warning")
            else:
                self._items[target].set_status("completed")

    def set_progress(self, pct: int) -> None:
        self.progress_bar.setValue(pct)
