"""Unit tests for the Storage reader and smartctl JSON telemetry parser."""

from unittest.mock import patch
import pytest

from inspectlog.core.models import Confidence, Status
from inspectlog.core.windows.storage_reader import (
    StorageReader,
    parse_smartctl_device_telemetry,
)


def test_parse_smartctl_sata_ssd(load_fixture):
    data = load_fixture("smartctl_sample.json")
    parsed = parse_smartctl_device_telemetry(data)

    assert parsed["model"] == "Samsung SSD 870 EVO 1TB"
    assert parsed["serial"] == "S6PENF0W123456K"
    assert parsed["firmware"] == "SVT02B6Q"
    assert parsed["capacity_bytes"] == 1000204886016
    assert parsed["smart_passed"] is True
    assert parsed["power_on_hours"] == 1250
    assert parsed["power_cycles"] == 312
    assert parsed["temperature_c"] == 32
    assert parsed["reallocated_sectors"] == 0
    assert parsed["pending_sectors"] == 0


def test_parse_smartctl_nvme_ssd(load_fixture):
    data = load_fixture("smartctl_nvme_sample.json")
    parsed = parse_smartctl_device_telemetry(data)

    assert parsed["model"] == "Samsung SSD 980 PRO 1TB"
    assert parsed["serial"] == "S5GXNF0R123456Z"
    assert parsed["smart_passed"] is True
    assert parsed["power_on_hours"] == 2800
    assert parsed["percentage_used"] == 3
    assert parsed["media_errors"] == 0
    assert parsed["temperature_c"] == 41
    assert parsed["tbw_gb"] > 10000  # ~11.9 TBW


def test_storage_reader_healthy(load_fixture):
    smart_data = load_fixture("smartctl_sample.json")
    wmi_disk = [{
        "DeviceID": r"\\.\PHYSICALDRIVE0",
        "Index": 0,
        "Model": "Samsung SSD 870 EVO 1TB",
        "SerialNumber": "S6PENF0W123456K",
        "InterfaceType": "IDE",
        "Size": "1000204886016",
        "Status": "OK",
    }]

    def _mock_smartctl(bin_path, args):
        if "--scan" in args:
            return {"devices": [{"name": "/dev/sda"}]}
        return smart_data

    reader = StorageReader()

    with patch("inspectlog.core.windows.storage_reader.find_smartctl_binary", return_value="smartctl.exe"), \
         patch("inspectlog.core.windows.storage_reader.run_smartctl_json", side_effect=_mock_smartctl), \
         patch("inspectlog.core.windows.storage_reader.safe_wmi_query", return_value=wmi_disk):
        results = reader.read_storage()

    assert len(results) == 1
    res = results[0]
    assert res.status == Status.PASS
    assert res.health_score == 100

    # Cross-validated model & serial
    assert res.readings["disk_model"].value == "Samsung SSD 870 EVO 1TB"
    assert res.readings["disk_model"].confidence == Confidence.HIGH
    assert res.readings["disk_serial"].value == "S6PENF0W123456K"
    assert res.readings["disk_serial"].confidence == Confidence.HIGH

    # SMART health
    assert res.readings["smart_health"].value == "Passed"
    assert res.readings["smart_health"].confidence == Confidence.HIGH
    assert "1250 hours" in res.readings["power_on_hours"].value


def test_storage_reader_smart_failing(load_fixture):
    smart_data = load_fixture("smartctl_sample.json")
    smart_data["smart_status"]["passed"] = False
    wmi_disk = [{
        "DeviceID": r"\\.\PHYSICALDRIVE0",
        "Index": 0,
        "Model": "Samsung SSD 870 EVO 1TB",
        "SerialNumber": "S6PENF0W123456K",
        "InterfaceType": "IDE",
        "Size": "1000204886016",
        "Status": "Pred Fail",
    }]

    def _mock_smartctl(bin_path, args):
        if "--scan" in args:
            return {"devices": [{"name": "/dev/sda"}]}
        return smart_data

    reader = StorageReader()

    with patch("inspectlog.core.windows.storage_reader.find_smartctl_binary", return_value="smartctl.exe"), \
         patch("inspectlog.core.windows.storage_reader.run_smartctl_json", side_effect=_mock_smartctl), \
         patch("inspectlog.core.windows.storage_reader.safe_wmi_query", return_value=wmi_disk):
        results = reader.read_storage()

    assert len(results) == 1
    res = results[0]
    assert res.status == Status.FAIL
    assert res.health_score == 0
    assert any("SMART" in err and "FAILURE" in err for err in res.errors)


def test_storage_reader_bad_sectors(load_fixture):
    smart_data = load_fixture("smartctl_sample.json")
    # Mutate attribute 5 to have 12 reallocated sectors
    for attr in smart_data["ata_smart_attributes"]["table"]:
        if attr["id"] == 5:
            attr["raw"]["value"] = 12

    wmi_disk = [{
        "DeviceID": r"\\.\PHYSICALDRIVE0",
        "Index": 0,
        "Model": "Samsung SSD 870 EVO 1TB",
        "SerialNumber": "S6PENF0W123456K",
        "InterfaceType": "IDE",
        "Size": "1000204886016",
        "Status": "OK",
    }]

    def _mock_smartctl(bin_path, args):
        if "--scan" in args:
            return {"devices": [{"name": "/dev/sda"}]}
        return smart_data

    reader = StorageReader()

    with patch("inspectlog.core.windows.storage_reader.find_smartctl_binary", return_value="smartctl.exe"), \
         patch("inspectlog.core.windows.storage_reader.run_smartctl_json", side_effect=_mock_smartctl), \
         patch("inspectlog.core.windows.storage_reader.safe_wmi_query", return_value=wmi_disk):
        results = reader.read_storage()

    res = results[0]
    assert res.status == Status.WARNING
    assert res.health_score < 100
    assert any("reallocated" in w.lower() for w in res.warnings)
