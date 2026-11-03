"""CPU multi-core stress workload with real-time thermal throttling detection."""

from __future__ import annotations

import concurrent.futures
import os
import threading
import time
from typing import Any, Callable

import numpy as np
import psutil

from hardwareverify.constants import (
    THERMAL_EMERGENCY_STOP_C,
    THERMAL_THROTTLE_DROP_PCT,
)
from hardwareverify.core.windows.wmi_helpers import safe_wmi_query
from hardwareverify.infra.logging import get_logger

logger = get_logger("cpu_stress")


def _read_current_cpu_temp() -> float | None:
    """Read current CPU temperature in °C via ACPI thermal zone WMI."""
    rows = safe_wmi_query(
        "MSAcpi_ThermalZoneTemperature",
        namespace="root/wmi",
        fields=["CurrentTemperature"],
    )
    if rows and rows[0].get("CurrentTemperature"):
        raw_k = rows[0]["CurrentTemperature"]
        # Formula: (tenths of Kelvin - 2732) / 10 = Celsius
        return round((raw_k - 2732) / 10.0, 1)
    return None


def _stress_worker(stop_event: threading.Event) -> None:
    """Intensive floating point matrix multiply worker loop."""
    matrix_dim = 256
    while not stop_event.is_set():
        a = np.random.rand(matrix_dim, matrix_dim).astype(np.float32)
        b = np.random.rand(matrix_dim, matrix_dim).astype(np.float32)
        _ = np.dot(a, b)


def run_cpu_stress_test(
    duration_s: int = 30,
    progress_callback: Callable[[int, str, dict[str, Any]], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Execute multi-core CPU stress test while logging temperatures and detecting throttling.

    Args:
        duration_s: Duration in seconds to run stress workload.
        progress_callback: Optional callback reporting (pct, status_msg, current_telemetry).
        cancel_check: Optional callable to check for user abort.

    Returns:
        Dict with keys:
            verdict: str ("Stable & Optimal", "Thermal Throttling Detected", etc.)
            max_temperature_c: float
            throttling_detected: bool
            avg_clock_mhz: float
            min_clock_mhz: float
            max_clock_mhz: float
            clock_drop_pct: float
            samples: list[dict]
            emergency_aborted: bool
            error_message: str | None
    """
    start_time = time.perf_counter()
    num_threads = psutil.cpu_count(logical=True) or 4
    stop_event = threading.Event()

    out: dict[str, Any] = {
        "verdict": "Stable & Optimal",
        "max_temperature_c": 0.0,
        "throttling_detected": False,
        "avg_clock_mhz": 0.0,
        "min_clock_mhz": 999999.0,
        "max_clock_mhz": 0.0,
        "clock_drop_pct": 0.0,
        "samples": [],
        "emergency_aborted": False,
        "error_message": None,
    }

    # Launch worker threads in pool
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=num_threads)
    futures = [executor.submit(_stress_worker, stop_event) for _ in range(num_threads)]

    clock_samples: list[float] = []
    temp_samples: list[float] = []
    baseline_clock = 0.0

    try:
        elapsed = 0
        while elapsed < duration_s:
            if cancel_check and cancel_check():
                out["error_message"] = "Stress test cancelled by user"
                break

            time.sleep(1.0)
            elapsed = int(time.perf_counter() - start_time)

            # Sample metrics
            freq = psutil.cpu_freq()
            cur_clock = freq.current if freq else 0.0
            cur_load = psutil.cpu_percent()
            cur_temp = _read_current_cpu_temp()

            if cur_clock > 0:
                clock_samples.append(cur_clock)
                out["max_clock_mhz"] = max(out["max_clock_mhz"], cur_clock)
                out["min_clock_mhz"] = min(out["min_clock_mhz"], cur_clock)

            if cur_temp is not None:
                temp_samples.append(cur_temp)
                out["max_temperature_c"] = max(out["max_temperature_c"], cur_temp)

                # Emergency Thermal Abort Guard
                if cur_temp >= THERMAL_EMERGENCY_STOP_C:
                    logger.critical("EMERGENCY THERMAL CUTOFF: CPU reached %s°C!", cur_temp)
                    out["emergency_aborted"] = True
                    out["verdict"] = f"CRITICAL: Emergency Abort at {cur_temp}°C (Overheating)"
                    out["error_message"] = f"CPU temperature exceeded safety threshold ({cur_temp}°C > {THERMAL_EMERGENCY_STOP_C}°C)"
                    break

            sample = {
                "second": elapsed,
                "clock_mhz": cur_clock,
                "load_pct": cur_load,
                "temp_c": cur_temp,
            }
            out["samples"].append(sample)

            # Record baseline clock after first 3 seconds
            if elapsed == 3 and clock_samples:
                baseline_clock = sum(clock_samples) / len(clock_samples)

            # Check for thermal throttling
            if baseline_clock > 0 and cur_clock > 0:
                drop = ((baseline_clock - cur_clock) / baseline_clock) * 100.0
                if drop > THERMAL_THROTTLE_DROP_PCT and (cur_temp is None or cur_temp > 75.0):
                    out["throttling_detected"] = True
                    out["clock_drop_pct"] = round(drop, 1)

            pct = min(100, int((elapsed / duration_s) * 100))
            if progress_callback:
                temp_text = f"{cur_temp}°C" if cur_temp else "N/A"
                progress_callback(
                    pct,
                    f"CPU Stress: {elapsed}/{duration_s}s | Clock: {int(cur_clock)} MHz | Temp: {temp_text}",
                    sample,
                )

    except Exception as e:
        logger.exception("Error during CPU stress test: %s", e)
        out["error_message"] = str(e)
    finally:
        stop_event.set()
        executor.shutdown(wait=False, cancel_futures=True)

    if clock_samples:
        out["avg_clock_mhz"] = round(sum(clock_samples) / len(clock_samples), 1)
    if out["min_clock_mhz"] == 999999.0:
        out["min_clock_mhz"] = 0.0

    # Final verdict assignment
    if not out["emergency_aborted"]:
        if out["throttling_detected"]:
            out["verdict"] = f"Thermal Throttling Detected ({out['clock_drop_pct']}% clock reduction under heat)"
        elif out["max_temperature_c"] > 88.0:
            out["verdict"] = f"High Operating Temperatures ({out['max_temperature_c']}°C peak)"
        else:
            out["verdict"] = "Stable & Optimal Performance"

    return out
