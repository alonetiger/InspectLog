"""Unit tests for the RAM reader and dual-channel topology analyzer."""

from unittest.mock import MagicMock, patch
import pytest

from hardwareverify.core.models import Confidence, Status
from hardwareverify.core.windows.ram_reader import RAMReader


def test_ram_reader_dual_channel(load_fixture):
    data = load_fixture("wmi_ram_sample.json")
    mem_rows = data["Win32_PhysicalMemory"]
    array_rows = data["Win32_PhysicalMemoryArray"]

    mock_vm = MagicMock()
    mock_vm.total = 16 * 1024 * 1024 * 1024  # 16 GB

    def _mock_query(wmi_class, namespace="root/cimv2", fields=None, where=None):
        if wmi_class == "Win32_PhysicalMemory":
            return mem_rows
        elif wmi_class == "Win32_PhysicalMemoryArray":
            return array_rows
        return []

    reader = RAMReader()

    with patch("hardwareverify.core.windows.ram_reader.safe_wmi_query", side_effect=_mock_query), \
         patch("psutil.virtual_memory", return_value=mock_vm):
        result = reader.read_ram()

    assert result.module_name == "ram"
    assert result.status == Status.PASS
    assert result.health_score == 100

    # Total RAM cross-validation
    total_val = result.readings["total_ram"]
    assert "16 GB" in total_val.value
    assert total_val.confidence == Confidence.HIGH

    # Dual-Channel
    dc_val = result.readings["dual_channel"]
    assert "Dual-Channel Active" in dc_val.value
    assert dc_val.confidence == Confidence.HIGH

    # Speed
    speed_val = result.readings["ram_speed"]
    assert "3200 MHz" in speed_val.value
    assert "DDR4" in speed_val.value


def test_ram_reader_single_channel():
    # Only 1 stick installed on 2-slot board
    mem_rows = [{
        "Capacity": 8589934592,
        "Speed": 3200,
        "ConfiguredClockSpeed": 3200,
        "Manufacturer": "Crucial",
        "PartNumber": "CT8G4SFRA32A",
        "DeviceLocator": "ChannelA-DIMM0",
        "BankLabel": "BANK 0",
        "SMBIOSMemoryType": 26,
    }]
    array_rows = [{"MemoryDevices": 2}]

    mock_vm = MagicMock()
    mock_vm.total = 8 * 1024 * 1024 * 1024

    def _mock_query(wmi_class, namespace="root/cimv2", fields=None, where=None):
        if wmi_class == "Win32_PhysicalMemory":
            return mem_rows
        elif wmi_class == "Win32_PhysicalMemoryArray":
            return array_rows
        return []

    reader = RAMReader()

    with patch("hardwareverify.core.windows.ram_reader.safe_wmi_query", side_effect=_mock_query), \
         patch("psutil.virtual_memory", return_value=mock_vm):
        result = reader.read_ram()

    dc_val = result.readings["dual_channel"]
    assert "Single-Channel" in dc_val.value
    assert any("Single-Channel" in w for w in result.warnings)


def test_ram_reader_underclocked_ram():
    # Rated at 3600MHz but running at 2133MHz base
    mem_rows = [{
        "Capacity": 17179869184,
        "Speed": 3600,
        "ConfiguredClockSpeed": 2133,
        "Manufacturer": "Corsair",
        "PartNumber": "CMK32GX4M2D3600C18",
        "DeviceLocator": "DIMM 1",
        "SMBIOSMemoryType": 26,
    }]
    array_rows = [{"MemoryDevices": 2}]

    mock_vm = MagicMock()
    mock_vm.total = 16 * 1024 * 1024 * 1024

    def _mock_query(wmi_class, namespace="root/cimv2", fields=None, where=None):
        if wmi_class == "Win32_PhysicalMemory":
            return mem_rows
        elif wmi_class == "Win32_PhysicalMemoryArray":
            return array_rows
        return []

    reader = RAMReader()

    with patch("hardwareverify.core.windows.ram_reader.safe_wmi_query", side_effect=_mock_query), \
         patch("psutil.virtual_memory", return_value=mock_vm):
        result = reader.read_ram()

    assert any("underclocked" in w.lower() or "below its rated" in w.lower() for w in result.warnings)
    assert result.health_score < 100
