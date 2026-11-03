"""Unit tests for the CPU reader and spoof detection engine."""

from unittest.mock import MagicMock, patch
import pytest

from hardwareverify.core.models import Confidence, Status
from hardwareverify.core.windows.cpu_reader import CPUReader
from hardwareverify.core.windows.cpu_spoof_db import verify_cpu_authenticity


def test_cpu_spoof_detector_genuine():
    is_auth, msg = verify_cpu_authenticity(
        model_name="13th Gen Intel(R) Core(TM) i7-13700H",
        physical_cores=14,
        logical_threads=20,
        l3_cache_mb=24.0,
    )
    assert is_auth is True
    assert "passed" in msg.lower() or "match" in msg.lower()


def test_cpu_spoof_detector_fake_i9():
    # Model claims to be i9-13900K (needs 24 cores / 32 threads) but only has 4 cores!
    is_auth, msg = verify_cpu_authenticity(
        model_name="13th Gen Intel(R) Core(TM) i9-13900K",
        physical_cores=4,
        logical_threads=8,
        l3_cache_mb=6.0,
    )
    assert is_auth is False
    assert "SPOOFED" in msg


def test_cpu_spoof_detector_fake_ryzen():
    # Model claims to be Ryzen 9 5900X (needs 12 cores / 24 threads) but only has 6 cores
    is_auth, msg = verify_cpu_authenticity(
        model_name="AMD Ryzen 9 5900X 12-Core Processor",
        physical_cores=6,
        logical_threads=12,
    )
    assert is_auth is False
    assert "SPOOFED" in msg


def test_cpu_reader_healthy(load_fixture):
    cinfo_data = load_fixture("cpuinfo_sample.json")
    wmi_data = load_fixture("wmi_cpu_sample.json")["Win32_Processor"]

    mock_freq = MagicMock()
    mock_freq.current = 2400.0
    mock_freq.max = 5000.0

    reader = CPUReader()

    with patch("cpuinfo.get_cpu_info", return_value=cinfo_data), \
         patch("psutil.cpu_count", side_effect=lambda logical=False: 20 if logical else 14), \
         patch("psutil.cpu_freq", return_value=mock_freq), \
         patch("hardwareverify.core.windows.cpu_reader.safe_wmi_query", return_value=wmi_data):
        result = reader.read_cpu()

    assert result.module_name == "cpu"
    assert result.status == Status.PASS
    assert result.health_score == 100

    # Cross-validated model
    assert "i7-13700H" in result.readings["cpu_model"].value
    assert result.readings["cpu_model"].confidence == Confidence.HIGH

    # Cores & Threads
    assert result.readings["cpu_cores"].value == 14
    assert result.readings["cpu_cores"].confidence == Confidence.HIGH
    assert result.readings["cpu_threads"].value == 20
    assert result.readings["cpu_threads"].confidence == Confidence.HIGH

    # Virtualization
    assert "Enabled in Firmware" in result.readings["cpu_virtualization"].value
    # Spoof check
    assert "Passed" in result.readings["cpu_spoof_check"].value


def test_cpu_reader_spoofed_detection(load_fixture):
    cinfo_data = load_fixture("cpuinfo_sample.json")
    # Mutate name to i9-13900K while cores remain 4
    cinfo_data["brand_raw"] = "Intel Core i9-13900K"

    wmi_data = [{
        "Name": "Intel Core i9-13900K",
        "NumberOfCores": 4,
        "NumberOfLogicalProcessors": 8,
        "MaxClockSpeed": 3400,
        "VirtualizationFirmwareEnabled": True,
    }]

    mock_freq = MagicMock()
    mock_freq.current = 3400.0
    mock_freq.max = 3400.0

    reader = CPUReader()

    with patch("cpuinfo.get_cpu_info", return_value=cinfo_data), \
         patch("psutil.cpu_count", side_effect=lambda logical=False: 8 if logical else 4), \
         patch("psutil.cpu_freq", return_value=mock_freq), \
         patch("hardwareverify.core.windows.cpu_reader.safe_wmi_query", return_value=wmi_data):
        result = reader.read_cpu()

    assert result.status == Status.FAIL
    assert result.health_score < 50
    assert any("SPOOFED" in err for err in result.errors)
