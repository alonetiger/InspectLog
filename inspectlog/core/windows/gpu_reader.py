"""Windows GPU reader with NVML deep telemetry and 64-bit VRAM verification."""

from __future__ import annotations

import time
from typing import Any
import winreg

from inspectlog.core.cross_validator import cross_validate, cross_validate_numeric
from inspectlog.core.models import (
    Confidence,
    DataSource,
    ModuleResult,
    Status,
    VerifiedValue,
)
from inspectlog.core.windows.wmi_helpers import safe_wmi_query
from inspectlog.infra.logging import get_logger

logger = get_logger("gpu_reader")

import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    try:
        import pynvml
        HAS_PYNVML = True
    except ImportError:
        HAS_PYNVML = False


def _read_registry_vram_bytes(adapter_index: int = 0) -> int | None:
    """Read the 64-bit HardwareInformation.qwMemorySize from Windows display class registry."""
    key_path = rf"SYSTEM\CurrentControlSet\Control\Class\{{4d36e968-e325-11ce-bfc1-08002be10318}}\{adapter_index:04d}"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as k:
            val, _ = winreg.QueryValueEx(k, "HardwareInformation.qwMemorySize")
            if isinstance(val, int) and val > 0:
                return val
    except Exception:
        pass
    return None


def _get_nvidia_telemetry() -> list[dict[str, Any]]:
    """Query NVIDIA NVML for installed GeForce/RTX/Quadro cards."""
    results: list[dict[str, Any]] = []
    if not HAS_PYNVML:
        return results

    try:
        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        driver_ver = pynvml.nvmlSystemGetDriverVersion()
        if isinstance(driver_ver, bytes):
            driver_ver = driver_ver.decode("utf-8")

        for i in range(count):
            h = pynvml.nvmlDeviceGetHandleByIndex(i)
            raw_name = pynvml.nvmlDeviceGetName(h)
            name = raw_name.decode("utf-8") if isinstance(raw_name, bytes) else str(raw_name)

            mem = pynvml.nvmlDeviceGetMemoryInfo(h)
            temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)

            results.append({
                "index": i,
                "name": name,
                "vram_total_bytes": mem.total,
                "vram_free_bytes": mem.free,
                "temperature_c": temp,
                "driver_version": driver_ver,
            })
    except Exception as e:
        logger.debug("NVML query note: %s", e)
    finally:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass

    return results


def _classify_gpu_type(name: str) -> str:
    """Classify GPU as Integrated or Dedicated."""
    lower = name.lower()
    integrated_keywords = [
        "intel(r) hd", "intel(r) uhd", "intel(r) iris", "intel hd",
        "intel uhd", "iris xe", "integrated", "vega 3", "vega 6",
        "vega 7", "vega 8", "radeon graphics", "basic display",
    ]
    for kw in integrated_keywords:
        if kw in lower:
            return "Integrated Graphics (Shared Memory)"

    dedicated_keywords = [
        "geforce", "rtx", "gtx", "quadro", "radeon rx",
        "radeon pro", "arc", "tesla",
    ]
    for kw in dedicated_keywords:
        if kw in lower:
            return "Dedicated Graphics (Discrete VRAM)"

    return "Dedicated Graphics"


class GPUReader:
    """Reads graphics adapters, verified physical VRAM, drivers, and thermals."""

    def read_gpu(self) -> list[ModuleResult]:
        """Enumerate all GPU controllers and return a list of ModuleResult."""
        results: list[ModuleResult] = []

        # 1. WMI Win32_VideoController
        wmi_gpus = safe_wmi_query(
            "Win32_VideoController",
            fields=[
                "Name",
                "AdapterRAM",
                "DriverVersion",
                "DriverDate",
                "VideoProcessor",
                "PNPDeviceID",
                "CurrentHorizontalResolution",
                "CurrentVerticalResolution",
                "CurrentRefreshRate",
            ],
        )

        # 2. NVIDIA NVML Telemetry
        nv_cards = _get_nvidia_telemetry()

        if not wmi_gpus and not nv_cards:
            empty_res = ModuleResult(
                module_name="gpu",
                display_name="Graphics (No GPU Detected)",
                status=Status.FAIL,
                health_score=0,
                icon="🎮",
            )
            empty_res.add_error("No display controllers or graphics adapters detected.")
            empty_res.finalize(0.0)
            return [empty_res]

        for idx, wgpu in enumerate(wmi_gpus):
            start_time = time.perf_counter()
            w_name = str(wgpu.get("Name") or f"Graphics Adapter {idx}").strip()
            w_driver = str(wgpu.get("DriverVersion") or "").strip()
            w_ram = wgpu.get("AdapterRAM")
            w_proc = str(wgpu.get("VideoProcessor") or "").strip()

            mod_result = ModuleResult(
                module_name=f"gpu_{idx}",
                display_name=f"Graphics: {w_name}",
                icon="🎮",
            )

            # Match with NVML card if NVIDIA
            matched_nv: dict[str, Any] | None = None
            for nv in nv_cards:
                if nv["name"].lower() in w_name.lower() or w_name.lower() in nv["name"].lower():
                    matched_nv = nv
                    break

            # A. GPU Model Name
            nv_name = matched_nv.get("name") if matched_nv else None
            name_val = cross_validate([
                ("WMI:Win32_VideoController.Name", w_name),
                ("NVIDIA NVML", nv_name),
            ])
            mod_result.add_reading("gpu_model", name_val)

            # B. Integrated vs Dedicated Classification
            gpu_type = _classify_gpu_type(w_name)
            mod_result.add_reading(
                "gpu_type",
                VerifiedValue.from_single(gpu_type, "Device ID / Model Heuristic"),
            )

            # C. VRAM Verification (Resolving 32-bit AdapterRAM 4GB Cap)
            reg_vram = _read_registry_vram_bytes(idx)
            nv_vram = matched_nv.get("vram_total_bytes") if matched_nv else None

            vram_bytes = nv_vram or reg_vram or (int(w_ram) if (w_ram and isinstance(w_ram, int) and w_ram > 0) else None)

            if vram_bytes:
                vram_gb = round(vram_bytes / (1024**3), 1)
                vram_str = f"{int(vram_gb)} GB VRAM" if vram_gb.is_integer() else f"{vram_gb} GB VRAM"

                vram_sources = []
                if nv_vram:
                    vram_sources.append(DataSource("NVIDIA NVML Hardware Query", f"{round(nv_vram/(1024**3), 2)} GB"))
                if reg_vram:
                    vram_sources.append(DataSource("Registry 64-bit qwMemorySize", f"{round(reg_vram/(1024**3), 2)} GB"))
                if w_ram:
                    vram_sources.append(DataSource("WMI:Win32_VideoController.AdapterRAM", f"{round(w_ram/(1024**3), 2)} GB"))

                conf = Confidence.HIGH if len(vram_sources) >= 2 else Confidence.MEDIUM
                mod_result.add_reading(
                    "gpu_vram",
                    VerifiedValue(
                        value=vram_str,
                        sources=vram_sources,
                        confidence=conf,
                    ),
                )
            else:
                mod_result.add_reading(
                    "gpu_vram",
                    VerifiedValue.from_single("Dynamic Shared Memory", "Integrated GPU Driver"),
                )

            # D. Driver Version
            nv_drv = matched_nv.get("driver_version") if matched_nv else None
            driver_val = cross_validate([
                ("WMI:DriverVersion", w_driver if w_driver else None),
                ("NVIDIA NVML", nv_drv),
            ])
            mod_result.add_reading("gpu_driver", driver_val)

            # E. Temperature
            nv_temp = matched_nv.get("temperature_c") if matched_nv else None
            if nv_temp is not None:
                mod_result.add_reading(
                    "gpu_temperature",
                    VerifiedValue.from_single(f"{nv_temp} °C", "NVIDIA NVML Thermal Sensor"),
                )
                if nv_temp > 85:
                    mod_result.add_warning(f"Elevated GPU temperature ({nv_temp} °C).")
                    mod_result.deduct_score(10)
            else:
                mod_result.add_reading(
                    "gpu_temperature",
                    VerifiedValue.unavailable("GPU thermal sensor unavailable or integrated graphics"),
                )

            duration = time.perf_counter() - start_time
            mod_result.finalize(duration)
            results.append(mod_result)

        return results
