"""Windows Thermal sensors, temperatures, and fan speed monitor."""

from __future__ import annotations

import time

from hardwareverify.core.models import (
    Confidence,
    DataSource,
    ModuleResult,
    Status,
    VerifiedValue,
)
from hardwareverify.core.windows.wmi_helpers import safe_wmi_query
from hardwareverify.infra.logging import get_logger

logger = get_logger("thermal_reader")


class ThermalReader:
    """Reads temperature sensors, fan RPMs, and thermal zone telemetry."""

    def read_thermals(self) -> ModuleResult:
        """Query all available temperature sensors and return a ModuleResult."""
        start_time = time.perf_counter()
        result = ModuleResult(
            module_name="thermals",
            display_name="Thermals & Fans",
            icon="🌡️",
        )

        # 1. ACPI Thermal Zone Temperatures
        tz_rows = safe_wmi_query(
            "MSAcpi_ThermalZoneTemperature",
            namespace="root/wmi",
            fields=["CurrentTemperature", "CriticalTripPoint", "InstanceName"],
        )

        cpu_temps: list[float] = []
        if tz_rows:
            for tz in tz_rows:
                raw_k = tz.get("CurrentTemperature")
                if isinstance(raw_k, (int, float)) and raw_k > 0:
                    c = round((raw_k - 2732) / 10.0, 1)
                    if 0 < c < 125:  # Valid sensor range
                        cpu_temps.append(c)

        if cpu_temps:
            avg_cpu = round(sum(cpu_temps) / len(cpu_temps), 1)
            result.add_reading(
                "cpu_temperature",
                VerifiedValue.from_single(
                    value=f"{avg_cpu} °C",
                    source_name="WMI:root/wmi:MSAcpi_ThermalZoneTemperature",
                    raw_value=tz_rows,
                ),
            )
            if avg_cpu > 85:
                result.add_warning(f"High idle/current CPU temperature ({avg_cpu} °C).")
                result.deduct_score(15)
        else:
            result.add_reading(
                "cpu_temperature",
                VerifiedValue.unavailable("ACPI thermal zone temperature not exposed by motherboard ACPI table"),
            )

        # 2. Fan RPMs
        fan_rows = safe_wmi_query("Win32_Fan", fields=["DesiredSpeed", "VariableSpeed", "Status"])
        # Check LibreHardwareMonitor / OpenHardwareMonitor WMI namespace if active
        lhm_fans = safe_wmi_query("Sensor", namespace="root/LibreHardwareMonitor", fields=["Name", "Value", "SensorType"], where="SensorType='Fan'")

        if lhm_fans:
            fan_val = lhm_fans[0].get("Value")
            result.add_reading(
                "fan_speed",
                VerifiedValue.from_single(f"{int(fan_val)} RPM", "WMI:LibreHardwareMonitor:Fan"),
            )
        elif fan_rows and fan_rows[0].get("DesiredSpeed"):
            result.add_reading(
                "fan_speed",
                VerifiedValue.from_single(f"{fan_rows[0]['DesiredSpeed']} RPM", "WMI:Win32_Fan"),
            )
        else:
            result.add_reading(
                "fan_speed",
                VerifiedValue.unavailable("Fan RPM sensor requires kernel driver (e.g. LibreHardwareMonitor)"),
            )

        # 3. Motherboard / CPU Voltages
        lhm_volts = safe_wmi_query("Sensor", namespace="root/LibreHardwareMonitor", fields=["Name", "Value", "SensorType"], where="SensorType='Voltage'")
        if lhm_volts:
            v_val = lhm_volts[0].get("Value")
            result.add_reading(
                "cpu_voltage",
                VerifiedValue.from_single(f"{round(float(v_val), 3)} V", "WMI:LibreHardwareMonitor:Voltage"),
            )
        else:
            result.add_reading(
                "cpu_voltage",
                VerifiedValue.unavailable("Voltage telemetry requires kernel sensor driver"),
            )

        duration = time.perf_counter() - start_time
        result.finalize(duration)
        return result
