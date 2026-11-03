"""Windows Battery hardware reader and health analyzer."""

from __future__ import annotations

from datetime import datetime
import os
import subprocess
import tempfile
import time
from typing import Any
import xml.etree.ElementTree as ET

import psutil

from hardwareverify.constants import (
    BATTERY_EXCELLENT_THRESHOLD,
    BATTERY_FAIR_THRESHOLD,
    BATTERY_GOOD_THRESHOLD,
)
from hardwareverify.core.cross_validator import cross_validate_numeric
from hardwareverify.core.models import (
    BatteryHealth,
    Confidence,
    DataSource,
    ModuleResult,
    Status,
    VerifiedValue,
)
from hardwareverify.core.windows.wmi_helpers import safe_wmi_query
from hardwareverify.infra.cleanup import cleanup_manager
from hardwareverify.infra.logging import get_logger

logger = get_logger("battery_reader")

CHEMISTRY_MAP = {
    1: "Other",
    2: "Unknown",
    3: "Lead Acid (PbAc)",
    4: "Nickel Cadmium (NiCd)",
    5: "Nickel Metal Hydride (NiMH)",
    6: "Lithium-ion (Li-ion)",
    7: "Zinc Air",
    8: "Lithium Polymer (LiP)",
}


def parse_powercfg_battery_xml(xml_content: str) -> dict[str, Any]:
    """Parse powercfg /batteryreport XML content and extract battery specs.

    Returns dict with keys:
        design_capacity: int (mWh) or None
        full_charge_capacity: int (mWh) or None
        cycle_count: int or None
        chemistry: str or None
        manufacturer: str or None
        serial: str or None
    """
    out: dict[str, Any] = {
        "design_capacity": None,
        "full_charge_capacity": None,
        "cycle_count": None,
        "chemistry": None,
        "manufacturer": None,
        "serial": None,
    }
    if not xml_content or not xml_content.strip():
        return out

    try:
        root = ET.fromstring(xml_content)
        # Search for Batteries / Battery elements
        batteries = root.findall(".//Batteries/Battery")
        if not batteries:
            batteries = root.findall(".//Battery")

        if batteries:
            b = batteries[0]
            design_elem = b.find("DesignCapacity")
            if design_elem is not None and design_elem.text and design_elem.text.isdigit():
                out["design_capacity"] = int(design_elem.text)

            full_elem = b.find("FullChargeCapacity")
            if full_elem is not None and full_elem.text and full_elem.text.isdigit():
                out["full_charge_capacity"] = int(full_elem.text)

            cycle_elem = b.find("CycleCount")
            if cycle_elem is not None and cycle_elem.text and cycle_elem.text.isdigit():
                out["cycle_count"] = int(cycle_elem.text)

            chem_elem = b.find("Chemistry")
            if chem_elem is not None and chem_elem.text:
                out["chemistry"] = chem_elem.text.strip()

            mfg_elem = b.find("Manufacturer")
            if mfg_elem is not None and mfg_elem.text:
                out["manufacturer"] = mfg_elem.text.strip()

            sn_elem = b.find("SerialNumber")
            if sn_elem is not None and sn_elem.text:
                out["serial"] = sn_elem.text.strip()
    except Exception as e:
        logger.warning("Error parsing powercfg XML: %s", e)

    return out


def fetch_powercfg_data() -> tuple[dict[str, Any], str | None]:
    """Run powercfg /batteryreport /xml and return parsed data and raw xml."""
    temp_xml = os.path.join(tempfile.gettempdir(), f"hwv_bat_{int(time.time()*1000)}.xml")
    cleanup_manager.register_file(temp_xml)
    try:
        res = subprocess.run(
            ["powercfg", "/batteryreport", "/xml", "/output", temp_xml],
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if res.returncode == 0 and os.path.exists(temp_xml):
            with open(temp_xml, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return parse_powercfg_battery_xml(content), content
    except Exception as e:
        logger.debug("powercfg execution failed: %s", e)
    finally:
        cleanup_manager.cleanup_file(temp_xml)

    return {}, None


class BatteryReader:
    """Reads laptop battery health, design/full capacity, cycle count, and wear."""

    def read_battery(self) -> ModuleResult:
        """Collect all battery telemetry and return a ModuleResult."""
        start_time = time.perf_counter()
        result = ModuleResult(
            module_name="battery",
            display_name="Battery",
            icon="🔋",
        )

        # 1. psutil quick sensor probe
        ps_bat = psutil.sensors_battery()
        is_ac_desktop = False
        if ps_bat is None:
            is_ac_desktop = True

        # 2. WMI telemetry (root/wmi namespace)
        static_rows = safe_wmi_query(
            "BatteryStaticData",
            namespace="root/wmi",
            fields=["DesignedCapacity", "ManufactureName", "UniqueID", "Chemistry"],
        )
        full_rows = safe_wmi_query(
            "BatteryFullChargedCapacity",
            namespace="root/wmi",
            fields=["FullChargedCapacity"],
        )
        cycle_rows = safe_wmi_query(
            "BatteryCycleCount",
            namespace="root/wmi",
            fields=["CycleCount"],
        )
        status_rows = safe_wmi_query(
            "BatteryStatus",
            namespace="root/wmi",
            fields=["ChargeRate", "DischargeRate", "Voltage", "PowerOnline", "Charging", "Discharging"],
        )

        # Fallback check Win32_Battery in root/cimv2 if root/wmi has no rows
        cim_bat_rows = safe_wmi_query("Win32_Battery", namespace="root/cimv2")

        # 3. powercfg data
        pcfg_data, raw_xml = fetch_powercfg_data()

        # Check if any battery exists
        has_battery = (
            bool(ps_bat is not None)
            or bool(static_rows)
            or bool(full_rows)
            or bool(cim_bat_rows)
            or bool(pcfg_data.get("design_capacity"))
        )

        if not has_battery:
            result.is_applicable = False
            result.status = Status.NOT_TESTED
            result.health_score = 100
            result.add_reading(
                "battery_present",
                VerifiedValue(
                    value=False,
                    sources=[
                        DataSource("psutil.sensors_battery()", None),
                        DataSource("WMI:root/wmi:BatteryStaticData", []),
                        DataSource("WMI:Win32_Battery", []),
                    ],
                    confidence=Confidence.HIGH,
                ),
            )
            result.add_reading(
                "battery_health",
                VerifiedValue.unavailable("No battery detected — standard for desktop PCs or devices on direct AC power."),
            )
            result.finalize(time.perf_counter() - start_time)
            return result

        # We have a battery!
        result.add_reading(
            "battery_present",
            VerifiedValue(
                value=True,
                sources=[
                    DataSource("psutil.sensors_battery()", bool(ps_bat)),
                    DataSource("WMI:BatteryStaticData", bool(static_rows)),
                ],
                confidence=Confidence.HIGH,
            ),
        )

        # A. Design Capacity
        wmi_design = static_rows[0].get("DesignedCapacity") if static_rows else None
        pcfg_design = pcfg_data.get("design_capacity")
        design_readings = [
            ("WMI:BatteryStaticData.DesignedCapacity", wmi_design if (isinstance(wmi_design, (int, float)) and wmi_design > 0) else None),
            ("powercfg /batteryreport:DesignCapacity", pcfg_design if (isinstance(pcfg_design, (int, float)) and pcfg_design > 0) else None),
        ]
        design_val = cross_validate_numeric(design_readings, tolerance_pct=3.0)
        result.add_reading("design_capacity", design_val)

        # B. Full Charge Capacity
        wmi_full = full_rows[0].get("FullChargedCapacity") if full_rows else None
        pcfg_full = pcfg_data.get("full_charge_capacity")
        full_readings = [
            ("WMI:BatteryFullChargedCapacity.FullChargedCapacity", wmi_full if (isinstance(wmi_full, (int, float)) and wmi_full > 0) else None),
            ("powercfg /batteryreport:FullChargeCapacity", pcfg_full if (isinstance(pcfg_full, (int, float)) and pcfg_full > 0) else None),
        ]
        full_val = cross_validate_numeric(full_readings, tolerance_pct=3.0)
        result.add_reading("full_charge_capacity", full_val)

        # C. Wear Percentage & Health Verdict
        wear_pct: float | None = None
        if design_val.is_available and full_val.is_available:
            des_num = float(design_val.value)
            full_num = float(full_val.value)
            if des_num > 0:
                wear_pct = round(max(0.0, (1.0 - (full_num / des_num)) * 100.0), 1)

        if wear_pct is not None:
            # Confidence matches minimum of the two inputs
            wear_conf = (
                Confidence.HIGH
                if (design_val.confidence == Confidence.HIGH and full_val.confidence == Confidence.HIGH)
                else Confidence.MEDIUM
            )
            result.add_reading(
                "wear_percentage",
                VerifiedValue(
                    value=wear_pct,
                    sources=[
                        DataSource("Calculated: (1 - Full/Design)*100", f"{wear_pct}%"),
                    ],
                    confidence=wear_conf,
                ),
            )

            # Health verdict
            if wear_pct < BATTERY_EXCELLENT_THRESHOLD:
                verdict = BatteryHealth.EXCELLENT
                desc = f"Excellent (Only {wear_pct}% wear)"
            elif wear_pct < BATTERY_GOOD_THRESHOLD:
                verdict = BatteryHealth.GOOD
                desc = f"Good ({wear_pct}% wear)"
            elif wear_pct < BATTERY_FAIR_THRESHOLD:
                verdict = BatteryHealth.FAIR
                desc = f"Fair ({wear_pct}% wear - noticeable degradation)"
                result.add_warning(f"Battery wear is {wear_pct}%. Noticeable runtime reduction.")
            else:
                verdict = BatteryHealth.REPLACE
                desc = f"Replace Required ({wear_pct}% wear - severely degraded)"
                result.add_warning(
                    f"Battery wear is {wear_pct}%. The battery has lost substantial capacity and should be replaced."
                )

            result.add_reading(
                "battery_health",
                VerifiedValue(
                    value=desc,
                    sources=[DataSource("Wear Evaluation Thresholds", desc)],
                    confidence=wear_conf,
                ),
            )

            # Deduct score according to wear:
            # <10% (Excellent): 0
            # 10-25% (Good): up to 15 pts
            # 25-40% (Fair): 15 to 37 pts (Warning zone)
            # >40% (Replace): 40+ pts (Fail zone)
            if wear_pct < BATTERY_EXCELLENT_THRESHOLD:
                deduction = 0
            elif wear_pct < BATTERY_GOOD_THRESHOLD:
                deduction = int((wear_pct - BATTERY_EXCELLENT_THRESHOLD) * 1.0)
            elif wear_pct < BATTERY_FAIR_THRESHOLD:
                deduction = 15 + int((wear_pct - BATTERY_GOOD_THRESHOLD) * 1.5)
            else:
                deduction = 40 + int((wear_pct - BATTERY_FAIR_THRESHOLD) * 2.0)

            deduction = min(60, deduction)
            result.deduct_score(deduction)
        else:
            result.add_reading(
                "wear_percentage",
                VerifiedValue.unavailable("Cannot compute wear without both design and full capacities"),
            )
            result.add_reading(
                "battery_health",
                VerifiedValue.unavailable("Cannot determine health verdict"),
            )
            result.deduct_score(15, "Battery wear could not be calculated from firmware data.")

        # D. Cycle Count
        cycle_cnt: int | None = None
        if cycle_rows and cycle_rows[0].get("CycleCount") is not None:
            cycle_cnt = cycle_rows[0].get("CycleCount")
        elif pcfg_data.get("cycle_count") is not None:
            cycle_cnt = pcfg_data.get("cycle_count")

        if cycle_cnt is not None and cycle_cnt >= 0:
            result.add_reading(
                "cycle_count",
                VerifiedValue.from_single(
                    value=cycle_cnt,
                    source_name="BatteryCycleCount / powercfg",
                    raw_value=cycle_cnt,
                ),
            )
            if cycle_cnt > 600:
                result.add_warning(f"High battery cycle count: {cycle_cnt} cycles.")
                result.deduct_score(10)
            elif cycle_cnt > 350:
                result.add_warning(f"Moderate battery cycles: {cycle_cnt} cycles.")
                result.deduct_score(5)
        else:
            result.add_reading(
                "cycle_count",
                VerifiedValue.unavailable("Cycle count not exposed by battery management controller (BMC/EC)"),
            )
            # Cycle count missing is fairly common on some OEM firmware, mild deduction
            result.deduct_score(5)

        # E. Chemistry
        chem_code = static_rows[0].get("Chemistry") if static_rows else None
        chem_name: str | None = None
        if isinstance(chem_code, int) and chem_code in CHEMISTRY_MAP:
            chem_name = CHEMISTRY_MAP[chem_code]
        elif pcfg_data.get("chemistry"):
            chem_name = pcfg_data.get("chemistry")

        if chem_name:
            result.add_reading(
                "chemistry",
                VerifiedValue.from_single(
                    value=chem_name,
                    source_name="WMI:BatteryStaticData.Chemistry",
                    raw_value=chem_code,
                ),
            )
        else:
            result.add_reading(
                "chemistry",
                VerifiedValue.unavailable("Battery chemistry not reported"),
            )

        # F. Current Charge / Discharge Rate & Voltage
        if status_rows:
            sr = status_rows[0]
            cr = sr.get("ChargeRate")
            dr = sr.get("DischargeRate")
            volt = sr.get("Voltage")
            online = sr.get("PowerOnline")

            if volt:
                result.add_reading(
                    "voltage",
                    VerifiedValue.from_single(
                        value=f"{volt} mV ({round(volt/1000.0, 2)} V)",
                        source_name="WMI:BatteryStatus.Voltage",
                        raw_value=volt,
                    ),
                )

            if dr and dr > 0:
                result.add_reading(
                    "discharge_rate",
                    VerifiedValue.from_single(
                        value=f"{dr} mW",
                        source_name="WMI:BatteryStatus.DischargeRate",
                        raw_value=dr,
                    ),
                )
            else:
                result.add_reading(
                    "discharge_rate",
                    VerifiedValue.from_single("0 mW (Not discharging / on AC)", "WMI:BatteryStatus.DischargeRate"),
                )

            if cr and cr > 0:
                result.add_reading(
                    "charge_rate",
                    VerifiedValue.from_single(
                        value=f"{cr} mW",
                        source_name="WMI:BatteryStatus.ChargeRate",
                        raw_value=cr,
                    ),
                )
            else:
                result.add_reading(
                    "charge_rate",
                    VerifiedValue.from_single("0 mW (Not charging)", "WMI:BatteryStatus.ChargeRate"),
                )

        # G. Current Percent & AC Status (psutil)
        if ps_bat:
            result.add_reading(
                "current_percent",
                VerifiedValue.from_single(
                    value=f"{ps_bat.percent}%",
                    source_name="psutil.sensors_battery().percent",
                    raw_value=ps_bat.percent,
                ),
            )
            result.add_reading(
                "power_plugged",
                VerifiedValue.from_single(
                    value="Plugged into AC" if ps_bat.power_plugged else "Running on Battery",
                    source_name="psutil.sensors_battery().power_plugged",
                    raw_value=ps_bat.power_plugged,
                ),
            )

        duration = time.perf_counter() - start_time
        result.finalize(duration)
        return result
