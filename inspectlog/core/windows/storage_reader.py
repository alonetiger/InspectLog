"""Windows Storage hardware reader parsing WMI and smartctl JSON telemetry."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from typing import Any

from inspectlog.constants import SMARTCTL_PATH
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

logger = get_logger("storage_reader")


def find_smartctl_binary() -> str | None:
    """Locate bundled or system-installed smartctl executable."""
    candidates = [
        SMARTCTL_PATH,
        os.path.join(os.path.dirname(SMARTCTL_PATH), "bin", "smartctl.exe"),
        shutil.which("smartctl"),
        r"C:\Program Files\smartmontools\bin\smartctl.exe",
        r"C:\Program Files (x86)\smartmontools\bin\smartctl.exe",
    ]
    for c in candidates:
        if c and os.path.exists(c) and os.path.isfile(c):
            return os.path.abspath(c)
    return None


def run_smartctl_json(smartctl_bin: str, args: list[str]) -> dict[str, Any] | None:
    """Execute smartctl with given arguments and return parsed JSON."""
    try:
        cmd = [smartctl_bin, *args, "--json"]
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if res.stdout and res.stdout.strip():
            return json.loads(res.stdout)
    except Exception as e:
        logger.debug("smartctl execution error for args %s: %s", args, e)
    return None


def parse_smartctl_device_telemetry(data: dict[str, Any]) -> dict[str, Any]:
    """Parse raw smartctl JSON dict into a normalized storage telemetry dict."""
    out: dict[str, Any] = {
        "model": None,
        "serial": None,
        "firmware": None,
        "capacity_bytes": None,
        "smart_passed": None,
        "power_on_hours": None,
        "power_cycles": None,
        "temperature_c": None,
        "reallocated_sectors": None,
        "pending_sectors": None,
        "media_errors": None,
        "percentage_used": None,
        "tbw_gb": None,
    }

    # Top-level identifiers
    out["model"] = data.get("model_name") or data.get("model_family")
    out["serial"] = data.get("serial_number")
    out["firmware"] = data.get("firmware_version")

    user_cap = data.get("user_capacity", {})
    if isinstance(user_cap, dict) and user_cap.get("bytes"):
        out["capacity_bytes"] = user_cap["bytes"]

    smart_status = data.get("smart_status", {})
    if isinstance(smart_status, dict) and "passed" in smart_status:
        out["smart_passed"] = bool(smart_status["passed"])

    poh = data.get("power_on_time", {})
    if isinstance(poh, dict) and "hours" in poh:
        out["power_on_hours"] = poh["hours"]

    if "power_cycle_count" in data:
        out["power_cycles"] = data["power_cycle_count"]

    temp = data.get("temperature", {})
    if isinstance(temp, dict) and "current" in temp:
        out["temperature_c"] = temp["current"]

    # NVMe SMART log format
    nvme_log = data.get("nvme_smart_health_information_log")
    if isinstance(nvme_log, dict):
        if "critical_warning" in nvme_log:
            out["smart_passed"] = (nvme_log["critical_warning"] == 0)
        if "percentage_used" in nvme_log:
            out["percentage_used"] = nvme_log["percentage_used"]
        if "media_errors" in nvme_log:
            out["media_errors"] = nvme_log["media_errors"]
        if "power_on_hours" in nvme_log and out["power_on_hours"] is None:
            out["power_on_hours"] = nvme_log["power_on_hours"]
        if "power_cycles" in nvme_log and out["power_cycles"] is None:
            out["power_cycles"] = nvme_log["power_cycles"]
        if "temperature" in nvme_log and out["temperature_c"] is None:
            out["temperature_c"] = nvme_log["temperature"]
        if "data_units_written" in nvme_log:
            # 1 data unit = 512,000 bytes
            raw_du = nvme_log["data_units_written"]
            out["tbw_gb"] = round((raw_du * 512000) / (1024**3), 1)

    # ATA SMART attributes table format
    ata_attrs = data.get("ata_smart_attributes", {}).get("table", [])
    if isinstance(ata_attrs, list):
        for attr in ata_attrs:
            attr_id = attr.get("id")
            raw_obj = attr.get("raw", {})
            raw_val = raw_obj.get("value") if isinstance(raw_obj, dict) else attr.get("raw_value")

            if attr_id == 5:  # Reallocated Sector Count
                out["reallocated_sectors"] = raw_val
            elif attr_id == 197:  # Current Pending Sector Count
                out["pending_sectors"] = raw_val
            elif attr_id == 9 and out["power_on_hours"] is None:
                out["power_on_hours"] = raw_val
            elif attr_id == 12 and out["power_cycles"] is None:
                out["power_cycles"] = raw_val
            elif attr_id in (190, 194) and out["temperature_c"] is None:
                if isinstance(raw_val, int) and raw_val < 150:
                    out["temperature_c"] = raw_val
            elif attr_id == 241 and out["tbw_gb"] is None:  # Total LBAs / Host writes
                if isinstance(raw_val, (int, float)):
                    # Attribute 241 is often in GiB or 32MB blocks depending on vendor
                    out["tbw_gb"] = round(raw_val * 32 / 1024, 1) if raw_val > 100000 else raw_val

    return out


class StorageReader:
    """Reads physical storage drives using smartctl and WMI."""

    def read_storage(self) -> list[ModuleResult]:
        """Enumerate all storage drives and return a list of ModuleResult."""
        results: list[ModuleResult] = []
        smartctl_bin = find_smartctl_binary()

        # 1. Query WMI Win32_DiskDrive
        wmi_disks = safe_wmi_query(
            "Win32_DiskDrive",
            fields=["DeviceID", "Index", "Model", "SerialNumber", "InterfaceType", "Size", "Status", "Partitions"],
        )

        # 2. Run smartctl --scan
        smart_devices: list[dict[str, Any]] = []
        if smartctl_bin:
            scan_data = run_smartctl_json(smartctl_bin, ["--scan"])
            if scan_data and "devices" in scan_data:
                smart_devices = scan_data["devices"]

        # If no disks found from either
        if not wmi_disks and not smart_devices:
            empty_res = ModuleResult(
                module_name="storage",
                display_name="Storage (No Drives Detected)",
                status=Status.FAIL,
                health_score=0,
                icon="💾",
            )
            empty_res.add_error("No physical storage devices detected via WMI or smartctl.")
            empty_res.finalize(0.0)
            return [empty_res]

        # Pre-fetch telemetry for all smart devices to enable smart serial/model matching
        smart_telemetries: list[tuple[str, dict[str, Any]]] = []
        if smartctl_bin:
            device_names = [d.get("name") for d in smart_devices] if smart_devices else [f"/dev/sd{chr(97+i)}" for i in range(len(wmi_disks) or 2)]
            for sname in device_names:
                if sname:
                    raw_sdata = run_smartctl_json(smartctl_bin, ["-a", sname])
                    if raw_sdata:
                        smart_telemetries.append((sname, parse_smartctl_device_telemetry(raw_sdata)))

        # Process each physical disk found in WMI
        if wmi_disks:
            for idx, wdisk in enumerate(wmi_disks):
                start_time = time.perf_counter()
                dev_id = wdisk.get("DeviceID", f"Drive_{idx}")
                w_model = str(wdisk.get("Model") or "").strip()
                w_serial = str(wdisk.get("SerialNumber") or "").strip()
                w_size = wdisk.get("Size")
                w_iface = str(wdisk.get("InterfaceType") or "").strip()
                w_status = str(wdisk.get("Status") or "").strip()

                disp_title = f"Storage: {w_model}" if w_model else f"Storage: Drive {idx}"
                mod_result = ModuleResult(
                    module_name=f"storage_{idx}",
                    display_name=disp_title,
                    icon="💾",
                )

                # Match strategy:
                # 1. Match by serial number (stripped, case-insensitive)
                # 2. Match by model substring
                # 3. Fallback to positional index
                matched_sdev = None
                s_telemetry: dict[str, Any] = {}

                norm_w_serial = w_serial.replace("_", "").replace(".", "").replace(" ", "").lower()
                norm_w_model = w_model.replace(" ", "").lower()

                for sname, stelem in smart_telemetries:
                    s_ser = str(stelem.get("serial") or "").replace("_", "").replace(".", "").replace(" ", "").lower()
                    s_mod = str(stelem.get("model") or "").replace(" ", "").lower()
                    if s_ser and norm_w_serial and (s_ser in norm_w_serial or norm_w_serial in s_ser):
                        matched_sdev = sname
                        s_telemetry = stelem
                        break
                    elif s_mod and norm_w_model and (s_mod in norm_w_model or norm_w_model in s_mod):
                        matched_sdev = sname
                        s_telemetry = stelem
                        break

                if not matched_sdev and smart_telemetries and idx < len(smart_telemetries):
                    matched_sdev, s_telemetry = smart_telemetries[idx]

                # A. Model Cross-validation
                s_model = s_telemetry.get("model")
                model_val = cross_validate([
                    ("smartctl", s_model),
                    ("WMI:Win32_DiskDrive.Model", w_model if w_model else None),
                ])
                mod_result.add_reading("disk_model", model_val)

                # B. Serial Cross-validation
                s_serial = s_telemetry.get("serial")
                serial_val = cross_validate([
                    ("smartctl", s_serial),
                    ("WMI:Win32_DiskDrive.SerialNumber", w_serial if w_serial else None),
                ])
                mod_result.add_reading("disk_serial", serial_val)

                # C. Capacity
                s_cap = s_telemetry.get("capacity_bytes")
                cap_val = cross_validate_numeric([
                    ("smartctl:user_capacity.bytes", s_cap),
                    ("WMI:Win32_DiskDrive.Size", int(w_size) if (w_size and str(w_size).isdigit()) else None),
                ], tolerance_pct=1.0)

                # Format human readable capacity
                if cap_val.is_available and cap_val.value:
                    gb = round(float(cap_val.value) / (1000**3), 1)
                    tb = round(gb / 1000, 2)
                    size_str = f"{tb} TB ({gb} GB)" if gb >= 1000 else f"{gb} GB"
                    cap_val.value = size_str
                mod_result.add_reading("disk_capacity", cap_val)

                # D. Interface & Firmware
                if s_telemetry.get("firmware"):
                    mod_result.add_reading(
                        "disk_firmware",
                        VerifiedValue.from_single(s_telemetry["firmware"], "smartctl"),
                    )

                mod_result.add_reading(
                    "disk_interface",
                    VerifiedValue.from_single(w_iface or "SATA / NVMe", "WMI:Win32_DiskDrive.InterfaceType"),
                )

                # E. SMART Health Verdict
                s_passed = s_telemetry.get("smart_passed")
                w_ok = (w_status.upper() == "OK")
                health_val = cross_validate([
                    ("smartctl:smart_status.passed", "Passed" if s_passed is True else ("Failing" if s_passed is False else None)),
                    ("WMI:Win32_DiskDrive.Status", "Passed" if w_ok else ("Failing" if w_status else None)),
                ])
                mod_result.add_reading("smart_health", health_val)

                if s_passed is False or not w_ok:
                    mod_result.add_error("SMART hardware self-test reports FAILURE! Replace drive immediately.")
                    mod_result.health_score = 0

                # F. Power-On Hours & Power Cycles
                poh = s_telemetry.get("power_on_hours")
                if poh is not None:
                    poh_val = VerifiedValue.from_single(f"{poh} hours ({round(poh/24, 1)} days)", "smartctl.power_on_time")
                    mod_result.add_reading("power_on_hours", poh_val)

                    if poh > 40000:
                        mod_result.add_warning(f"High drive lifetime usage: {poh} power-on hours (~{int(poh/8760)} years).")
                        mod_result.deduct_score(15)
                    elif poh > 25000:
                        mod_result.add_warning(f"Drive has {poh} power-on hours.")
                        mod_result.deduct_score(5)
                else:
                    mod_result.add_reading(
                        "power_on_hours",
                        VerifiedValue.unavailable("Power-on hours requires smartctl with elevated permissions"),
                    )

                cycles = s_telemetry.get("power_cycles")
                if cycles is not None:
                    mod_result.add_reading(
                        "power_cycles",
                        VerifiedValue.from_single(cycles, "smartctl.power_cycle_count"),
                    )

                # G. Reallocated & Pending Sectors
                realloc = s_telemetry.get("reallocated_sectors")
                if realloc is not None:
                    mod_result.add_reading(
                        "reallocated_sectors",
                        VerifiedValue.from_single(realloc, "smartctl:Reallocated_Sector_Ct"),
                    )
                    if realloc > 0:
                        mod_result.add_warning(f"Drive has {realloc} reallocated bad sectors. Indicates media deterioration.")
                        mod_result.deduct_score(min(40, realloc * 5))
                else:
                    mod_result.add_reading(
                        "reallocated_sectors",
                        VerifiedValue.from_single(0, "smartctl:NoReallocReported") if s_passed else VerifiedValue.unavailable("Not reported by controller"),
                    )

                pending = s_telemetry.get("pending_sectors")
                if pending is not None:
                    mod_result.add_reading(
                        "pending_sectors",
                        VerifiedValue.from_single(pending, "smartctl:Current_Pending_Sector"),
                    )
                    if pending > 0:
                        mod_result.add_warning(f"Drive has {pending} uncorrectable/pending sectors waiting for reallocation.")
                        mod_result.deduct_score(min(40, pending * 10))

                # H. Total Data Written (TBW)
                tbw = s_telemetry.get("tbw_gb")
                if tbw is not None:
                    tbw_str = f"{round(tbw/1000, 2)} TB" if tbw >= 1000 else f"{tbw} GB"
                    mod_result.add_reading(
                        "total_data_written",
                        VerifiedValue.from_single(tbw_str, "smartctl:HostWrites"),
                    )

                # I. Drive Temperature
                temp_c = s_telemetry.get("temperature_c")
                if temp_c is not None:
                    mod_result.add_reading(
                        "disk_temperature",
                        VerifiedValue.from_single(f"{temp_c} °C", "smartctl.temperature"),
                    )
                    if temp_c > 65:
                        mod_result.add_warning(f"High drive temperature ({temp_c} °C). Check airflow.")
                        mod_result.deduct_score(10)
                else:
                    mod_result.add_reading(
                        "disk_temperature",
                        VerifiedValue.unavailable("Temperature sensor not exposed by disk controller"),
                    )

                duration = time.perf_counter() - start_time
                mod_result.finalize(duration)
                results.append(mod_result)
        else:
            # Fallback for smartctl-only devices
            for idx, sdev in enumerate(smart_devices):
                sname = sdev.get("name", f"/dev/sd{chr(97+idx)}")
                sdata = run_smartctl_json(smartctl_bin, ["-a", sname])
                if sdata:
                    telemetry = parse_smartctl_device_telemetry(sdata)
                    mname = telemetry.get("model") or sname
                    mod_res = ModuleResult(
                        module_name=f"storage_{idx}",
                        display_name=f"Storage: {mname}",
                        icon="💾",
                    )
                    mod_res.add_reading("disk_model", VerifiedValue.from_single(mname, "smartctl"))
                    mod_res.finalize(0.1)
                    results.append(mod_res)

        return results
