"""Scan orchestrator and asynchronous worker threads for hardware scans."""

from __future__ import annotations

import time
from typing import Callable

from PySide6.QtCore import QObject, QThread, Signal

from inspectlog.core.hal_interface import HardwareReaderInterface
from inspectlog.core.models import ModuleResult, Status
from inspectlog.core.platform_factory import create_hal
from inspectlog.infra.config import ScanConfig
from inspectlog.infra.logging import get_logger

logger = get_logger("orchestrator")


class ScanWorker(QThread):
    """Background worker thread that runs all hardware module checks sequentially."""

    # Qt Signals
    module_started = Signal(str, str)         # module_name, display_name
    module_completed = Signal(str, object)     # module_name, ModuleResult
    module_error = Signal(str, str)            # module_name, error_message
    scan_progress = Signal(int)                # 0-100 percentage
    scan_completed = Signal(list)              # list of ModuleResult
    scan_cancelled = Signal()

    def __init__(self, hal: HardwareReaderInterface, config: ScanConfig) -> None:
        super().__init__()
        self._hal = hal
        self._config = config
        self._cancelled = False

    def cancel(self) -> None:
        """Flag the worker to stop processing modules."""
        self._cancelled = True

    def run(self) -> None:
        """Run the ordered hardware scanning tasks."""
        results: list[ModuleResult] = []
        sequence = self._build_sequence()
        total_steps = len(sequence)

        logger.info("Scan worker started with %d modules (quick_scan=%s)", total_steps, self._config.quick_scan)

        for i, (mod_id, display_name, reader_fn) in enumerate(sequence):
            if self._cancelled:
                logger.info("Scan worker cancelled by user.")
                self.scan_cancelled.emit()
                return

            self.module_started.emit(mod_id, display_name)

            try:
                mod_result = reader_fn()
                if isinstance(mod_result, list):
                    for r in mod_result:
                        results.append(r)
                    # Emit completion for the parent mod_id so progress tracking properly updates
                    summary_res = mod_result[0] if mod_result else None
                    self.module_completed.emit(mod_id, summary_res)
                elif mod_result is not None:
                    results.append(mod_result)
                    self.module_completed.emit(mod_id, mod_result)
            except Exception as e:
                logger.exception("Error executing module %s: %s", mod_id, e)
                err_result = ModuleResult(
                    module_name=mod_id,
                    display_name=display_name,
                    status=Status.FAIL,
                    health_score=0,
                )
                err_result.add_error(f"Module check failed unexpectedly: {e}")
                results.append(err_result)
                self.module_error.emit(mod_id, str(e))
                self.module_completed.emit(mod_id, err_result)

            pct = int(((i + 1) / total_steps) * 100)
            self.scan_progress.emit(min(100, pct))

        logger.info("Scan worker completed successfully.")
        self.scan_completed.emit(results)

    def _build_sequence(self) -> list[tuple[str, str, Callable]]:
        """Construct the ordered list of checks based on active configuration."""
        all_checks: list[tuple[str, str, Callable]] = [
            ("system_identity", "System Identity", self._hal.read_system_identity),
            ("battery", "Battery", self._hal.read_battery),
            ("storage", "Storage", self._hal.read_storage),
            ("ram", "RAM", self._hal.read_ram),
            ("cpu", "CPU", self._hal.read_cpu),
            ("gpu", "GPU", self._hal.read_gpu),
            ("display", "Display", self._hal.read_display),
            ("thermals", "Thermals & Fans", self._hal.read_thermals),
            ("security", "Security & Locks", self._hal.read_security),
            ("input_io", "Input & Peripherals", self._hal.read_input),
        ]

        # Filter against enabled modules in ScanConfig
        enabled = set(self._config.enabled_modules)
        return [c for c in all_checks if c[0] in enabled]


class ScanOrchestrator(QObject):
    """High-level orchestrator managing scan execution and signal forwarding."""

    module_started = Signal(str, str)
    module_completed = Signal(str, object)
    module_error = Signal(str, str)
    scan_progress = Signal(int)
    scan_completed = Signal(list)
    scan_cancelled = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._worker: ScanWorker | None = None
        self._hal: HardwareReaderInterface | None = None

    @property
    def is_running(self) -> bool:
        """True if a scan is currently active."""
        return self._worker is not None and self._worker.isRunning()

    def start_scan(self, config: ScanConfig) -> None:
        """Start a new scan job in a background thread."""
        if self.is_running:
            logger.warning("Scan requested while another scan is already running.")
            return

        if self._hal is None:
            self._hal = create_hal()

        self._worker = ScanWorker(self._hal, config)
        self._worker.module_started.connect(self.module_started)
        self._worker.module_completed.connect(self.module_completed)
        self._worker.module_error.connect(self.module_error)
        self._worker.scan_progress.connect(self.scan_progress)
        self._worker.scan_completed.connect(self._on_worker_completed)
        self._worker.scan_cancelled.connect(self._on_worker_cancelled)

        self._worker.start()

    def cancel_scan(self) -> None:
        """Cancel the active scan job."""
        if self._worker and self._worker.isRunning():
            self._worker.cancel()

    def _on_worker_completed(self, results: list[ModuleResult]) -> None:
        self.scan_completed.emit(results)
        self._worker = None

    def _on_worker_cancelled(self) -> None:
        self.scan_cancelled.emit()
        self._worker = None
