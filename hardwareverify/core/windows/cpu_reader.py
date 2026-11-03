"""Windows CPU hardware reader and spoof detection engine."""

from __future__ import annotations

import time
from typing import Any

import cpuinfo
import psutil

from hardwareverify.core.cross_validator import cross_validate, cross_validate_numeric
from hardwareverify.core.models import (
    Confidence,
    DataSource,
    ModuleResult,
    Status,
    VerifiedValue,
)
from hardwareverify.core.windows.cpu_spoof_db import verify_cpu_authenticity
from hardwareverify.core.windows.wmi_helpers import safe_wmi_query
from hardwareverify.infra.logging import get_logger

logger = get_logger("cpu_reader")


class CPUReader:
    """Reads processor specifications, cores/threads, cache, virtualization, and checks for spoofing."""

    def read_cpu(self) -> ModuleResult:
        """Collect all CPU telemetry and return a ModuleResult."""
        start_time = time.perf_counter()
        result = ModuleResult(
            module_name="cpu",
            display_name="Processor (CPU)",
            icon="⚡",
        )

        # 1. py-cpuinfo query
        cinfo: dict[str, Any] = {}
        try:
            cinfo = cpuinfo.get_cpu_info()
        except Exception as e:
            logger.warning("cpuinfo failed: %s", e)

        # 2. psutil core counts & frequencies
        ps_phys_cores = psutil.cpu_count(logical=False) or 1
        ps_log_threads = psutil.cpu_count(logical=True) or ps_phys_cores
        ps_freq = psutil.cpu_freq()

        # 3. WMI Win32_Processor
        proc_rows = safe_wmi_query(
            "Win32_Processor",
            fields=[
                "Name",
                "NumberOfCores",
                "NumberOfLogicalProcessors",
                "MaxClockSpeed",
                "CurrentClockSpeed",
                "L2CacheSize",
                "L3CacheSize",
                "VirtualizationFirmwareEnabled",
                "Manufacturer",
            ],
        )

        wmi_proc = proc_rows[0] if proc_rows else {}
        wmi_model = str(wmi_proc.get("Name") or "").strip()
        wmi_cores = wmi_proc.get("NumberOfCores")
        wmi_threads = wmi_proc.get("NumberOfLogicalProcessors")
        wmi_max_mhz = wmi_proc.get("MaxClockSpeed")
        wmi_virt = wmi_proc.get("VirtualizationFirmwareEnabled")
        wmi_l3 = wmi_proc.get("L3CacheSize")  # in KB

        # A. CPU Model Name Cross-validation
        cinfo_model = cinfo.get("brand_raw")
        model_readings = [
            ("py-cpuinfo", cinfo_model),
            ("WMI:Win32_Processor.Name", wmi_model if wmi_model else None),
        ]
        model_val = cross_validate(model_readings)
        result.add_reading("cpu_model", model_val)

        # B. Physical Cores Cross-validation
        cores_readings = [
            ("psutil.cpu_count(logical=False)", ps_phys_cores),
            ("WMI:Win32_Processor.NumberOfCores", wmi_cores if (isinstance(wmi_cores, int) and wmi_cores > 0) else None),
        ]
        cores_val = cross_validate_numeric(cores_readings, tolerance_pct=0.0)
        resolved_cores = int(cores_val.value or ps_phys_cores)
        result.add_reading("cpu_cores", cores_val)

        # C. Logical Threads
        threads_readings = [
            ("psutil.cpu_count(logical=True)", ps_log_threads),
            ("WMI:Win32_Processor.NumberOfLogicalProcessors", wmi_threads if (isinstance(wmi_threads, int) and wmi_threads > 0) else None),
        ]
        threads_val = cross_validate_numeric(threads_readings, tolerance_pct=0.0)
        resolved_threads = int(threads_val.value or ps_log_threads)
        result.add_reading("cpu_threads", threads_val)

        # D. Base / Max Clock Speeds
        if ps_freq and ps_freq.max:
            boost_mhz = int(ps_freq.max)
        elif wmi_max_mhz:
            boost_mhz = int(wmi_max_mhz)
        else:
            boost_mhz = None

        if boost_mhz:
            ghz = round(boost_mhz / 1000.0, 2)
            result.add_reading(
                "cpu_boost_clock",
                VerifiedValue.from_single(f"{boost_mhz} MHz ({ghz} GHz)", "WMI/psutil:MaxClock"),
            )

        # E. Cache Sizes
        l3_mb = None
        if cinfo.get("l3_cache_size"):
            l3_mb = round(cinfo["l3_cache_size"] / (1024 * 1024), 1)
        elif wmi_l3:
            l3_mb = round(wmi_l3 / 1024, 1)

        l2_mb = round(cinfo["l2_cache_size"] / (1024 * 1024), 1) if cinfo.get("l2_cache_size") else None

        cache_parts = []
        if l2_mb:
            cache_parts.append(f"L2: {l2_mb} MB")
        if l3_mb:
            cache_parts.append(f"L3: {l3_mb} MB")

        cache_str = " | ".join(cache_parts) if cache_parts else "Cache not reported"
        result.add_reading(
            "cpu_cache",
            VerifiedValue.from_single(cache_str, "py-cpuinfo / WMI CacheSize") if cache_parts else VerifiedValue.unavailable("Cache info unavailable"),
        )

        # F. Virtualization (VT-x / AMD-V)
        flags = cinfo.get("flags", [])
        has_vt_flag = "vmx" in flags or "svm" in flags
        is_virt_enabled = wmi_virt if wmi_virt is not None else has_vt_flag

        virt_str = (
            "Enabled in Firmware (VT-x / AMD-V)"
            if is_virt_enabled
            else ("Supported but Disabled in BIOS" if has_vt_flag else "Not Supported")
        )
        result.add_reading(
            "cpu_virtualization",
            VerifiedValue(
                value=virt_str,
                sources=[
                    DataSource("py-cpuinfo.flags", "vmx/svm found" if has_vt_flag else "none"),
                    DataSource("WMI:VirtualizationFirmwareEnabled", wmi_virt),
                ],
                confidence=Confidence.HIGH,
            ),
        )

        # G. CPU Spoof & Authenticity Check
        model_str = str(model_val.value or "")
        is_authentic, reason = verify_cpu_authenticity(
            model_name=model_str,
            physical_cores=resolved_cores,
            logical_threads=resolved_threads,
            l3_cache_mb=l3_mb,
        )

        if not is_authentic:
            result.add_reading(
                "cpu_spoof_check",
                VerifiedValue(
                    value="FAILED: Possible Fake / Spoofed CPU",
                    sources=[DataSource("Spoof Database Check", reason)],
                    confidence=Confidence.HIGH,
                ),
            )
            result.add_error(reason)
            result.deduct_score(60)
        else:
            result.add_reading(
                "cpu_spoof_check",
                VerifiedValue(
                    value="Passed (Authentic hardware specs)",
                    sources=[DataSource("Spoof Database Check", reason)],
                    confidence=Confidence.HIGH,
                ),
            )

        duration = time.perf_counter() - start_time
        result.finalize(duration)
        return result
