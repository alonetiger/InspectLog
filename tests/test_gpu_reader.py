"""Unit tests for the GPU reader and VRAM verification."""

from unittest.mock import patch
import pytest

from inspectlog.core.models import Confidence, Status
from inspectlog.core.windows.gpu_reader import GPUReader, _classify_gpu_type


def test_classify_gpu_type():
    assert "Integrated" in _classify_gpu_type("Intel(R) Iris(R) Xe Graphics")
    assert "Integrated" in _classify_gpu_type("Intel UHD Graphics 620")
    assert "Dedicated" in _classify_gpu_type("NVIDIA GeForce RTX 4070")
    assert "Dedicated" in _classify_gpu_type("AMD Radeon RX 7800 XT")


def test_gpu_reader_dual_gpu(load_fixture):
    wmi_data = load_fixture("wmi_gpu_sample.json")["Win32_VideoController"]
    nvml_data = [{
        "index": 0,
        "name": "NVIDIA GeForce RTX 4060 Laptop GPU",
        "vram_total_bytes": 8589934592,  # 8 GB VRAM
        "vram_free_bytes": 7000000000,
        "temperature_c": 45,
        "driver_version": "536.67",
    }]

    reader = GPUReader()

    with patch("inspectlog.core.windows.gpu_reader.safe_wmi_query", return_value=wmi_data), \
         patch("inspectlog.core.windows.gpu_reader._get_nvidia_telemetry", return_value=nvml_data):
        results = reader.read_gpu()

    assert len(results) == 2

    # GPU 0: Intel Iris Xe (Integrated)
    intel_gpu = results[0]
    assert "Iris" in intel_gpu.readings["gpu_model"].value
    assert "Integrated" in intel_gpu.readings["gpu_type"].value

    # GPU 1: RTX 4060 (Dedicated, 8GB VRAM verified from NVML)
    nv_gpu = results[1]
    assert "RTX 4060" in nv_gpu.readings["gpu_model"].value
    assert "Dedicated" in nv_gpu.readings["gpu_type"].value
    assert "8 GB VRAM" in nv_gpu.readings["gpu_vram"].value
    assert nv_gpu.readings["gpu_vram"].confidence == Confidence.HIGH
    assert nv_gpu.readings["gpu_temperature"].value == "45 °C"
