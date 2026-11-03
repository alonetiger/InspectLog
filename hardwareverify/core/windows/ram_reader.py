"""Windows RAM reader analyzing physical memory, slot topology, and dual-channel status."""

from __future__ import annotations

import time
from typing import Any

import psutil

from hardwareverify.core.cross_validator import cross_validate, cross_validate_numeric
from hardwareverify.core.models import (
    Confidence,
    DataSource,
    ModuleResult,
    Status,
    VerifiedValue,
)
from hardwareverify.core.windows.wmi_helpers import safe_wmi_query
from hardwareverify.infra.logging import get_logger

logger = get_logger("ram_reader")

MEMORY_TYPE_MAP = {
    20: "DDR",
    21: "DDR2",
    22: "DDR2 FB-DIMM",
    24: "DDR3",
    26: "DDR4",
    27: "LPDDR4",
    28: "LPDDR4X",
    30: "DDR5",
    31: "LPDDR5",
    34: "DDR5",
    35: "LPDDR5X",
}

FORM_FACTOR_MAP = {
    8: "DIMM (Desktop)",
    12: "SODIMM (Laptop)",
}


class RAMReader:
    """Reads system memory capacity, per-slot modules, speeds, and dual-channel topology."""

    def read_ram(self) -> ModuleResult:
        """Collect all memory telemetry and return a ModuleResult."""
        start_time = time.perf_counter()
        result = ModuleResult(
            module_name="ram",
            display_name="Memory (RAM)",
            icon="🧠",
        )

        # 1. psutil virtual memory
        vm = psutil.virtual_memory()
        total_bytes_ps = vm.total

        # 2. WMI Win32_PhysicalMemory
        mem_rows = safe_wmi_query(
            "Win32_PhysicalMemory",
            fields=[
                "Capacity",
                "Speed",
                "ConfiguredClockSpeed",
                "Manufacturer",
                "PartNumber",
                "DeviceLocator",
                "BankLabel",
                "SMBIOSMemoryType",
                "FormFactor",
            ],
        )

        # 3. WMI Win32_PhysicalMemoryArray (Total slots on motherboard)
        array_rows = safe_wmi_query(
            "Win32_PhysicalMemoryArray",
            fields=["MaxCapacity", "MemoryDevices"],
        )

        total_slots = None
        if array_rows and array_rows[0].get("MemoryDevices"):
            total_slots = int(array_rows[0]["MemoryDevices"])

        # Calculate total physical memory from WMI modules
        wmi_total_bytes = 0
        dimm_details: list[dict[str, Any]] = []

        if mem_rows:
            for r in mem_rows:
                cap = int(r.get("Capacity") or 0)
                wmi_total_bytes += cap
                speed = r.get("Speed")
                cfg_speed = r.get("ConfiguredClockSpeed")
                mfg = str(r.get("Manufacturer") or "Unknown").strip()
                part = str(r.get("PartNumber") or "").strip()
                locator = str(r.get("DeviceLocator") or "Slot").strip()
                bank = str(r.get("BankLabel") or "").strip()
                mtype_code = r.get("SMBIOSMemoryType")
                ff_code = r.get("FormFactor")

                mtype_str = MEMORY_TYPE_MAP.get(mtype_code, "DDR")
                ff_str = FORM_FACTOR_MAP.get(ff_code, "DIMM")

                dimm_details.append({
                    "capacity_bytes": cap,
                    "speed": speed,
                    "configured_speed": cfg_speed,
                    "manufacturer": mfg,
                    "part_number": part,
                    "locator": locator,
                    "bank": bank,
                    "type": mtype_str,
                    "form_factor": ff_str,
                })

        # A. Total RAM Cross-validation
        total_readings = [
            ("psutil.virtual_memory().total", total_bytes_ps),
            ("WMI:Win32_PhysicalMemory (Sum)", wmi_total_bytes if wmi_total_bytes > 0 else None),
        ]
        # Allow 15% tolerance because hardware-reserved RAM (integrated GPU, BIOS) reduces psutil total
        total_val = cross_validate_numeric(total_readings, tolerance_pct=15.0)

        # Prefer the raw hardware capacity sum if available
        reported_bytes = wmi_total_bytes if wmi_total_bytes > 0 else total_bytes_ps
        total_gb = round(reported_bytes / (1024**3), 1)
        total_val.value = f"{int(total_gb)} GB" if total_gb.is_integer() else f"{total_gb} GB"
        result.add_reading("total_ram", total_val)

        # B. Populated Slots vs Total Slots
        populated_count = len(dimm_details)
        slots_str = (
            f"{populated_count} of {total_slots} slots populated"
            if total_slots
            else f"{populated_count} module(s) installed"
        )
        result.add_reading(
            "ram_slots",
            VerifiedValue.from_single(
                value=slots_str,
                source_name="WMI:Win32_PhysicalMemory",
                raw_value={"populated": populated_count, "total_slots": total_slots},
            ),
        )

        # C. Dual-Channel Detection
        if populated_count >= 2:
            dual_channel = True
            dc_desc = f"Dual-Channel Active ({populated_count} modules detected)"
            dc_conf = Confidence.HIGH
        elif populated_count == 1:
            dual_channel = False
            dc_desc = "Single-Channel (Only 1 module installed)"
            dc_conf = Confidence.HIGH
            if total_slots and total_slots >= 2:
                result.add_warning(
                    "System is operating in Single-Channel mode. "
                    "Installing a second matching RAM stick will enable Dual-Channel and improve memory bandwidth."
                )
        else:
            dual_channel = False
            dc_desc = "Unknown channel mode"
            dc_conf = Confidence.LOW

        result.add_reading(
            "dual_channel",
            VerifiedValue(
                value=dc_desc,
                sources=[DataSource("DIMM Topology & Slot Count", {"populated": populated_count, "slots": total_slots})],
                confidence=dc_conf,
            ),
        )

        # D. RAM Speed (Actual vs Rated)
        if dimm_details:
            speeds = [d["speed"] for d in dimm_details if d.get("speed")]
            cfg_speeds = [d["configured_speed"] for d in dimm_details if d.get("configured_speed")]
            primary_type = dimm_details[0]["type"]

            running_mhz = cfg_speeds[0] if cfg_speeds else (speeds[0] if speeds else None)
            rated_mhz = speeds[0] if speeds else running_mhz

            if running_mhz:
                if rated_mhz and running_mhz < rated_mhz:
                    speed_summary = f"{running_mhz} MHz ({primary_type}) — Underclocked (Rated: {rated_mhz} MHz)"
                    result.add_warning(
                        f"RAM is running at {running_mhz} MHz, below its rated {rated_mhz} MHz. "
                        f"XMP/EXPO memory profile may be disabled in BIOS."
                    )
                    result.deduct_score(5)
                else:
                    speed_summary = f"{running_mhz} MHz ({primary_type})"

                result.add_reading(
                    "ram_speed",
                    VerifiedValue.from_single(
                        value=speed_summary,
                        source_name="WMI:Win32_PhysicalMemory.ConfiguredClockSpeed",
                        raw_value={"running": running_mhz, "rated": rated_mhz},
                    ),
                )
            else:
                result.add_reading(
                    "ram_speed",
                    VerifiedValue.unavailable("Memory clock speed not reported by SMBIOS/WMI"),
                )

            # E. Per-slot module breakdown
            for i, dimm in enumerate(dimm_details):
                slot_cap_gb = round(dimm["capacity_bytes"] / (1024**3), 1)
                slot_info = (
                    f"{int(slot_cap_gb)}GB {dimm['type']}-{dimm['configured_speed'] or dimm['speed']}MHz "
                    f"({dimm['manufacturer']} {dimm['part_number']}) [{dimm['locator']}]"
                )
                result.add_reading(
                    f"dimm_slot_{i+1}",
                    VerifiedValue.from_single(slot_info, f"WMI:Win32_PhysicalMemory[{i}]", dimm),
                )
        else:
            result.add_reading("ram_speed", VerifiedValue.unavailable("No physical memory modules detected in WMI"))
            result.add_error("WMI query for Win32_PhysicalMemory returned no modules.")
            result.deduct_score(30)

        duration = time.perf_counter() - start_time
        result.finalize(duration)
        return result
