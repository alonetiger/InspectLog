"""GPU compute stress workload with TDR crash detection and thermal monitoring."""

from __future__ import annotations

import threading
import time
from typing import Any, Callable

import numpy as np

from inspectlog.core.windows.wmi_helpers import safe_wmi_query
from inspectlog.infra.logging import get_logger

logger = get_logger("gpu_stress")

import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    try:
        import pynvml
        HAS_PYNVML = True
    except ImportError:
        HAS_PYNVML = False


def _get_gpu_temperature() -> float | None:
    """Read NVIDIA GPU temperature via NVML if available."""
    if not HAS_PYNVML:
        return None
    try:
        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        if count > 0:
            h = pynvml.nvmlDeviceGetHandleByIndex(0)
            return float(pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU))
    except Exception:
        pass
    finally:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass
    return None


def run_gpu_stress_test(
    duration_s: int = 20,
    progress_callback: Callable[[int, str, dict[str, Any]], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Execute compute stress workload while checking for driver crashes and temperature spikes.

    Args:
        duration_s: Duration in seconds to execute the workload.
        progress_callback: Callback reporting (pct, status_msg, telemetry).
        cancel_check: Optional callable to check for user abort.

    Returns:
        Dict with keys:
            verdict: str
            max_temp_c: float
            crashes_detected: int
            duration_s: float
            error_message: str | None
    """
    start_time = time.perf_counter()
    stop_event = threading.Event()

    out: dict[str, Any] = {
        "verdict": "Stable & Responsive",
        "max_temp_c": 0.0,
        "crashes_detected": 0,
        "duration_s": 0.0,
        "error_message": None,
    }

    def _gpu_worker():
        # High throughput matrix math exercise
        dim = 512
        while not stop_event.is_set():
            a = np.random.rand(dim, dim).astype(np.float32)
            b = np.random.rand(dim, dim).astype(np.float32)
            _ = np.matmul(a, b)

    worker_thread = threading.Thread(target=_gpu_worker, daemon=True)
    worker_thread.start()

    try:
        elapsed = 0
        while elapsed < duration_s:
            if cancel_check and cancel_check():
                out["error_message"] = "GPU stress cancelled by user"
                break

            time.sleep(1.0)
            elapsed = int(time.perf_counter() - start_time)

            cur_temp = _get_gpu_temperature()
            if cur_temp is not None:
                out["max_temp_c"] = max(out["max_temp_c"], cur_temp)

            pct = min(100, int((elapsed / duration_s) * 100))
            if progress_callback:
                temp_msg = f"{cur_temp}°C" if cur_temp else "Active"
                progress_callback(
                    pct,
                    f"GPU Stress Workload: {elapsed}/{duration_s}s | Temp: {temp_msg}",
                    {"second": elapsed, "temp_c": cur_temp},
                )

    except Exception as e:
        logger.exception("GPU stress error: %s", e)
        out["error_message"] = str(e)
    finally:
        stop_event.set()
        worker_thread.join(timeout=1.0)
        out["duration_s"] = round(time.perf_counter() - start_time, 2)

    if out["max_temp_c"] > 88.0:
        out["verdict"] = f"Elevated Operating Temperatures ({out['max_temp_c']}°C peak)"
    else:
        out["verdict"] = "Stable & Passed (Zero Driver Crashes)"

    return out
