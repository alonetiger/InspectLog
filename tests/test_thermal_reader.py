"""Unit tests for the thermal and fan speed reader."""

from unittest.mock import patch
import pytest

from inspectlog.core.models import Status
from inspectlog.core.windows.thermal_reader import ThermalReader


def test_thermal_reader_with_acpi():
    # 3152 tenths of Kelvin -> (3152 - 2732)/10 = 42.0 °C
    wmi_tz = [{
        "CurrentTemperature": 3152,
        "CriticalTripPoint": 3732,
    }]

    reader = ThermalReader()

    with patch("inspectlog.core.windows.thermal_reader.safe_wmi_query", side_effect=lambda cls, **kwargs: wmi_tz if "ThermalZone" in cls else []):
        result = reader.read_thermals()

    assert result.module_name == "thermals"
    assert result.status == Status.PASS
    assert "42.0 °C" in result.readings["cpu_temperature"].value
    assert result.readings["cpu_temperature"].is_available is True


def test_thermal_reader_unavailable():
    reader = ThermalReader()

    with patch("inspectlog.core.windows.thermal_reader.safe_wmi_query", return_value=[]):
        result = reader.read_thermals()

    assert not result.readings["cpu_temperature"].is_available
    assert not result.readings["fan_speed"].is_available
    assert "kernel driver" in result.readings["fan_speed"].unavailable_reason.lower()
