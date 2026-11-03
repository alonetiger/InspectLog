"""Unit tests for Windows display and monitor reader."""

from unittest.mock import patch
import pytest

from inspectlog.core.models import Confidence, Status
from inspectlog.core.windows.display_reader import DisplayReader


def test_decode_edid_chars():
    reader = DisplayReader()
    # Test decoding tuple of ASCII codes e.g. 'CMN'
    raw = (67, 77, 78, 0, 0, 0)
    assert reader._decode_edid_chars(raw) == "CMN"

    # Test non-tuple or empty
    assert reader._decode_edid_chars(None) == ""
    assert reader._decode_edid_chars([]) == ""


def test_build_edid_display_result_calculation():
    reader = DisplayReader()

    mid = {
        "InstanceName": "DISPLAY\\CMN15C6\\0",
        "ManufacturerName": (67, 77, 78, 0),
        "ProductCodeID": (49, 53, 67, 54, 0),
        "SerialNumberID": (48, 0),
        "UserFriendlyName": None,
        "YearOfManufacture": 2018,
        "WeekOfManufacture": 25,
    }
    params = {
        "InstanceName": "DISPLAY\\CMN15C6\\0",
        "MaxHorizontalImageSize": 34,
        "MaxVerticalImageSize": 19,
    }
    conn = {
        "InstanceName": "DISPLAY\\CMN15C6\\0",
        "VideoOutputTechnology": -2147483648,
    }

    result = reader._build_edid_display_result(
        idx=0,
        inst="display\\cmn15c6\\0",
        mid=mid,
        params=params,
        conn=conn,
        api_width=1366,
        api_height=768,
        api_freq=60,
        api_bpp=32,
        wmi_width=1366,
        wmi_height=768,
        wmi_freq=60,
        wmi_bpp=32,
        duration=0.05,
    )

    assert result.module_name == "display"
    assert result.status == Status.PASS
    assert "Chi Mei Innolux" in result.display_name

    # Check panel size calculation: sqrt(34^2 + 19^2) / 2.54 = ~15.3"
    assert '15.3"' in result.readings["panel_size"].value
    assert result.readings["panel_size"].confidence == Confidence.HIGH

    # Check resolution cross-validation (both agree -> HIGH)
    assert result.readings["resolution"].value == "1366 x 768"
    assert result.readings["resolution"].confidence == Confidence.HIGH

    # Check refresh rate
    assert result.readings["refresh_rate"].value == "60 Hz"
    assert result.readings["refresh_rate"].confidence == Confidence.HIGH

    # Check connection type mapping
    assert "Internal Display" in result.readings["connection_type"].value


def test_display_resolution_mismatch_warning():
    reader = DisplayReader()

    mid = {
        "ManufacturerName": (68, 69, 76, 0),  # DEL (Dell)
        "ProductCodeID": (48, 48, 49, 0),
    }

    result = reader._build_edid_display_result(
        idx=0,
        inst="display\\del001\\0",
        mid=mid,
        params=None,
        conn=None,
        api_width=1920,
        api_height=1080,
        api_freq=60,
        api_bpp=32,
        wmi_width=1366,
        wmi_height=768,
        wmi_freq=60,
        wmi_bpp=32,
        duration=0.05,
    )

    # Because Win32 and WMI resolutions disagree, confidence must drop to LOW and warning added
    assert result.readings["resolution"].confidence == Confidence.LOW
    assert any("mismatch" in w.lower() for w in result.warnings)
    assert result.status == Status.WARNING


def test_basic_display_fallback():
    reader = DisplayReader()
    result = reader._build_basic_display_result(
        api_width=1920,
        api_height=1080,
        api_freq=144,
        api_bpp=24,
        wmi_width=None,
        wmi_height=None,
        wmi_freq=None,
        wmi_bpp=None,
        duration=0.02,
    )

    assert result.status == Status.PASS
    assert result.readings["resolution"].value == "1920 x 1080"
    assert result.readings["refresh_rate"].value == "144 Hz"
