"""Unit tests for Windows input and peripheral reader."""

from unittest.mock import MagicMock, patch
import pytest

from hardwareverify.core.models import Confidence, Status
from hardwareverify.core.windows.input_reader import InputReader


def test_input_reader_components():
    reader = InputReader()

    with patch("hardwareverify.core.windows.input_reader.safe_wmi_query") as mock_wmi, \
         patch("subprocess.run") as mock_subproc:

        # Mock netsh wlan show interfaces
        mock_subproc.side_effect = [
            MagicMock(
                stdout=b"    Description : Realtek RTL8723BE 802.11 bgn Wi-Fi Adapter\n    State : connected\n    SSID : MyHomeWiFi\n"
            ),
            # Mock netsh wlan show networks
            MagicMock(
                stdout=b"SSID 1 : MyHomeWiFi\nSSID 2 : GuestWiFi\nSSID 3 : Office5G\n"
            ),
        ]

        # Mock WMI queries
        def fake_wmi_query(wmi_class, fields=None, where=None):
            if wmi_class == "Win32_NetworkAdapter":
                return [{"Name": "Realtek RTL8723BE 802.11 bgn Wi-Fi Adapter"}]
            elif wmi_class == "Win32_PnPEntity" and where and "Bluetooth" in where:
                return [{"Name": "Realtek Bluetooth 4.0 Adapter", "PNPClass": "Bluetooth"}]
            elif wmi_class == "Win32_PnPEntity" and where and "Biometric" in where:
                return [{"Name": "Synaptics FP Sensor", "PNPClass": "Biometric"}]
            elif wmi_class == "Win32_SoundDevice":
                return [{"Name": "Realtek High Definition Audio", "Status": "OK"}]
            elif wmi_class == "Win32_Keyboard":
                return [{"Description": "Standard PS/2 Keyboard", "Status": "OK"}]
            elif wmi_class == "Win32_PointingDevice":
                return [{"Description": "Microsoft PS/2 Mouse", "Status": "OK"}]
            elif wmi_class == "Win32_USBController":
                return [{"Name": "Intel(R) USB 3.0 Host Controller", "Status": "OK"}]
            return []

        mock_wmi.side_effect = fake_wmi_query

        result = reader.read_input()

        assert result.module_name == "input_io"
        assert result.status == Status.PASS

        # Wi-Fi checks
        assert "Realtek RTL8723BE" in result.readings["wifi_adapter"].value
        assert "MyHomeWiFi" in result.readings["wifi_adapter"].value
        assert result.readings["wifi_adapter"].confidence == Confidence.HIGH
        assert "3 network(s)" in result.readings["nearby_wifi_networks"].value

        # Bluetooth
        assert "Realtek Bluetooth" in result.readings["bluetooth_adapter"].value

        # Biometrics
        assert "Synaptics FP Sensor" in result.readings["biometric_sensor"].value

        # Audio
        assert "Realtek High Definition Audio" in result.readings["audio_controller"].value

        # Input devices
        assert "Standard PS/2 Keyboard" in result.readings["keyboard_hardware"].value
        assert "Microsoft PS/2 Mouse" in result.readings["pointing_hardware"].value
        assert "Intel(R) USB 3.0" in result.readings["usb_controllers"].value
