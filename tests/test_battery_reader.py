"""Unit tests for the Windows Battery hardware reader."""

from unittest.mock import MagicMock, patch

import pytest

from hardwareverify.core.models import BatteryHealth, Confidence, Status
from hardwareverify.core.windows.battery_reader import (
    BatteryReader,
    parse_powercfg_battery_xml,
)


def mock_safe_wmi_query_factory(fixture_data: dict):
    def _mock_query(wmi_class: str, namespace: str = "root/cimv2", fields=None, where=None):
        return fixture_data.get(wmi_class, [])
    return _mock_query


def test_parse_powercfg_battery_xml(load_text_fixture):
    xml_content = load_text_fixture("powercfg_sample.xml")
    parsed = parse_powercfg_battery_xml(xml_content)

    assert parsed["design_capacity"] == 54000
    assert parsed["full_charge_capacity"] == 48600
    assert parsed["cycle_count"] == 42
    assert parsed["chemistry"] == "LION"
    assert parsed["manufacturer"] == "Simplo"
    assert parsed["serial"] == "12894"


def test_battery_reader_healthy(load_fixture, load_text_fixture):
    wmi_data = load_fixture("wmi_battery_sample.json")
    xml_content = load_text_fixture("powercfg_sample.xml")
    reader = BatteryReader()

    mock_ps = MagicMock()
    mock_ps.percent = 85
    mock_ps.power_plugged = True

    with patch("hardwareverify.core.windows.battery_reader.safe_wmi_query", side_effect=mock_safe_wmi_query_factory(wmi_data)), \
         patch("hardwareverify.core.windows.battery_reader.fetch_powercfg_data", return_value=(parse_powercfg_battery_xml(xml_content), xml_content)), \
         patch("psutil.sensors_battery", return_value=mock_ps):
        result = reader.read_battery()

    assert result.module_name == "battery"
    assert result.status == Status.PASS
    assert result.health_score >= 80

    # Cross-validated capacities
    des_val = result.readings["design_capacity"]
    full_val = result.readings["full_charge_capacity"]
    assert des_val.value == 54000
    assert des_val.confidence == Confidence.HIGH
    assert full_val.value == 48600
    assert full_val.confidence == Confidence.HIGH

    # Wear calculation: (1 - 48600/54000)*100 = 10.0%
    wear_val = result.readings["wear_percentage"]
    assert wear_val.value == 10.0

    # Chemistry and Cycle Count
    assert "Lithium-ion" in result.readings["chemistry"].value
    assert result.readings["cycle_count"].value == 42


def test_battery_reader_worn_battery():
    # 54000 design, 35000 full charge -> 35.1% wear (FAIR)
    wmi_data = {
        "BatteryStaticData": [{"DesignedCapacity": 54000, "Chemistry": 6}],
        "BatteryFullChargedCapacity": [{"FullChargedCapacity": 35000}],
        "BatteryCycleCount": [{"CycleCount": 450}],
    }
    pcfg = {"design_capacity": 54000, "full_charge_capacity": 35000, "cycle_count": 450}

    reader = BatteryReader()

    with patch("hardwareverify.core.windows.battery_reader.safe_wmi_query", side_effect=mock_safe_wmi_query_factory(wmi_data)), \
         patch("hardwareverify.core.windows.battery_reader.fetch_powercfg_data", return_value=(pcfg, "")), \
         patch("psutil.sensors_battery", return_value=None):
        result = reader.read_battery()

    assert result.status == Status.WARNING
    assert result.health_score < 75
    wear_val = result.readings["wear_percentage"]
    assert 35.0 <= wear_val.value <= 35.2
    assert "Fair" in result.readings["battery_health"].value


def test_battery_reader_no_battery_desktop():
    reader = BatteryReader()

    with patch("hardwareverify.core.windows.battery_reader.safe_wmi_query", return_value=[]), \
         patch("hardwareverify.core.windows.battery_reader.fetch_powercfg_data", return_value=({}, None)), \
         patch("psutil.sensors_battery", return_value=None):
        result = reader.read_battery()

    # Desktop PCs return NOT_TESTED with 100 score and no crash
    assert result.status == Status.NOT_TESTED
    assert result.health_score == 100
    assert result.readings["battery_present"].value is False
    assert len(result.errors) == 0
