"""Unit tests for the Windows System Identity reader."""

import json
from unittest.mock import patch

import pytest

from hardwareverify.core.models import Confidence, Status
from hardwareverify.core.windows.system_reader import SystemReader, parse_wmi_date


def mock_safe_wmi_query_factory(fixture_data: dict):
    def _mock_query(wmi_class: str, namespace: str = "root/cimv2", fields=None, where=None):
        return fixture_data.get(wmi_class, [])
    return _mock_query


def test_parse_wmi_date():
    date_str, dt = parse_wmi_date("20231015000000.000000+000")
    assert date_str == "2023-10-15"
    assert dt.year == 2023
    assert dt.month == 10
    assert dt.day == 15

    # None input
    d_none, dt_none = parse_wmi_date(None)
    assert d_none is None
    assert dt_none is None


def test_system_reader_healthy(load_fixture):
    data = load_fixture("wmi_system_sample.json")
    reader = SystemReader()

    with patch("hardwareverify.core.windows.system_reader.safe_wmi_query", side_effect=mock_safe_wmi_query_factory(data)):
        result = reader.read_system_identity()

    assert result.module_name == "system_identity"
    assert result.status == Status.PASS
    assert result.health_score == 100

    # Manufacturer & Model
    assert result.readings["manufacturer"].value == "Dell Inc."
    assert result.readings["model"].value == "Latitude 5540"

    # Serial Number cross-validation
    serial_val = result.readings["serial_number"]
    assert serial_val.value == "8H2K9Z3"
    assert serial_val.confidence == Confidence.HIGH

    # BIOS
    assert result.readings["bios_version"].value == "1.8.0"
    assert result.readings["bios_date"].value == "2023-10-15"

    # Motherboard
    assert "08Y3ND" in result.readings["motherboard"].value

    # Activation
    assert result.readings["windows_activation"].value == "Activated (Licensed)"
    assert len(result.errors) == 0
    assert len(result.warnings) == 0


def test_system_reader_fake_serial(load_fixture):
    data = load_fixture("wmi_system_sample.json")
    # Mutate serial to fake OEM string
    data["Win32_BIOS"][0]["SerialNumber"] = "To be filled by O.E.M."
    data["Win32_SystemEnclosure"][0]["SerialNumber"] = "To be filled by O.E.M."

    reader = SystemReader()

    with patch("hardwareverify.core.windows.system_reader.safe_wmi_query", side_effect=mock_safe_wmi_query_factory(data)):
        result = reader.read_system_identity()

    assert result.status == Status.WARNING
    assert result.health_score < 100
    assert any("placeholder serial" in w.lower() for w in result.warnings)


def test_system_reader_empty_wmi():
    reader = SystemReader()

    with patch("hardwareverify.core.windows.system_reader.safe_wmi_query", return_value=[]):
        result = reader.read_system_identity()

    assert result.module_name == "system_identity"
    assert not result.readings["manufacturer"].is_available
    assert not result.readings["model"].is_available
    assert not result.readings["serial_number"].is_available
    assert result.readings["manufacturer"].unavailable_reason is not None


def test_system_reader_unlicensed(load_fixture):
    data = load_fixture("wmi_system_sample.json")
    data["SoftwareLicensingProduct"][0]["LicenseStatus"] = 5  # Notification (Unlicensed)

    reader = SystemReader()

    with patch("hardwareverify.core.windows.system_reader.safe_wmi_query", side_effect=mock_safe_wmi_query_factory(data)):
        result = reader.read_system_identity()

    assert result.status == Status.WARNING
    assert any("not genuinely activated" in w.lower() for w in result.warnings)
    assert result.health_score < 100
