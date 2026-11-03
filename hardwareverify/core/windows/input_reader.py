"""Windows Input and Peripherals Reader implementation.

Scans Wi-Fi, Bluetooth, Audio codecs/endpoints, Webcams, USB Host Controllers,
Keyboard and Touchpad hardware devices via WMI and Windows system tools.
"""

from __future__ import annotations

import subprocess
import time
from typing import Any

from hardwareverify.core.cross_validator import cross_validate
from hardwareverify.core.models import (
    Confidence,
    DataSource,
    ModuleResult,
    Status,
    VerifiedValue,
)
from hardwareverify.core.windows.wmi_helpers import safe_wmi_query
from hardwareverify.infra.logging import get_logger

logger = get_logger("input_reader")


class InputReader:
    """Reads input devices, wireless adapters, audio codecs, cameras, and USB controllers."""

    def read_input(self) -> ModuleResult:
        """Read all input and peripheral hardware controllers on the system.

        Returns a ModuleResult summarizing peripheral hardware status.
        """
        logger.info("Reading input, audio, wireless, and peripheral telemetry")
        t0 = time.time()

        result = ModuleResult(
            module_name="input_io",
            display_name="Input & Peripherals",
            status=Status.PASS,
            icon="🎮",
            health_score=100,
            is_applicable=True,
        )

        # 1. Wi-Fi Wireless Interface & Nearby Networks
        self._read_wifi(result)

        # 2. Bluetooth Radios
        self._read_bluetooth(result)

        # 3. Biometrics / Windows Hello
        self._read_biometrics(result)

        # 4. Audio Codecs & Endpoints
        self._read_audio(result)

        # 5. Webcams & Imaging Devices
        self._read_cameras(result)

        # 6. Keyboard & Touchpad Controllers
        self._read_input_controllers(result)

        # 7. USB Host Controllers & Hubs
        self._read_usb_controllers(result)

        # 8. Interactive Diagnostic Tests Status
        result.add_reading(
            "interactive_tests",
            VerifiedValue(
                value="Not Tested (Run Interactive Diagnostics)",
                confidence=Confidence.MEDIUM,
                sources=[DataSource(name="DiagnosticSuite", raw_value="Pending user execution")],
            ),
        )

        duration = time.time() - t0
        result.finalize(duration)
        return result

    def _read_wifi(self, result: ModuleResult) -> None:
        """Query Wi-Fi adapter state and scan nearby wireless networks."""
        adapter_name = None
        mac_addr = None
        state = None
        ssid = None

        try:
            res = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                timeout=5,
            )
            out = res.stdout.decode("cp437", errors="replace")
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("Description") and ":" in line:
                    adapter_name = line.split(":", 1)[1].strip()
                elif line.startswith("Physical address") and ":" in line:
                    mac_addr = line.split(":", 1)[1].strip()
                elif line.startswith("State") and ":" in line:
                    state = line.split(":", 1)[1].strip()
                elif line.startswith("SSID") and not line.startswith("BSSID") and ":" in line:
                    ssid = line.split(":", 1)[1].strip()
        except Exception as e:
            logger.warning("netsh wlan show interfaces query failed: %s", e)

        # Cross-check with WMI Win32_NetworkAdapter
        wmi_adapters = safe_wmi_query(
            "Win32_NetworkAdapter",
            where="AdapterType LIKE '%802.3%' OR NetConnectionID LIKE '%Wi-Fi%' OR NetConnectionID LIKE '%Wireless%'",
        )
        wmi_wifi_name = None
        for a in wmi_adapters:
            name = a.get("Name") or a.get("Description") or ""
            if any(k in name.lower() for k in ("wi-fi", "wireless", "802.11", "wlan")):
                wmi_wifi_name = name
                break

        wifi_sources: list[DataSource] = []
        if adapter_name:
            wifi_sources.append(DataSource(name="netsh:wlan", raw_value=f"{adapter_name} ({state or 'Unknown'})"))
        if wmi_wifi_name:
            wifi_sources.append(DataSource(name="WMI:Win32_NetworkAdapter", raw_value=wmi_wifi_name))

        if wifi_sources:
            display_str = adapter_name or wmi_wifi_name
            if ssid and state == "connected":
                display_str += f" [Connected to: {ssid}]"
            elif state:
                display_str += f" [{state.capitalize()}]"

            result.add_reading(
                "wifi_adapter",
                VerifiedValue(
                    value=display_str,
                    confidence=Confidence.HIGH if len(wifi_sources) >= 2 else Confidence.MEDIUM,
                    sources=wifi_sources,
                ),
            )
        else:
            result.add_reading(
                "wifi_adapter",
                VerifiedValue.unavailable(
                    reason="No Wi-Fi wireless network adapter detected on this system",
                ),
            )

        # Nearby networks count
        try:
            res_net = subprocess.run(
                ["netsh", "wlan", "show", "networks"],
                capture_output=True,
                timeout=5,
            )
            out_net = res_net.stdout.decode("cp437", errors="replace")
            ssids = [
                l.split(":", 1)[1].strip()
                for l in out_net.splitlines()
                if "SSID" in l and not "BSSID" in l and ":" in l and l.split(":", 1)[1].strip()
            ]
            result.add_reading(
                "nearby_wifi_networks",
                VerifiedValue(
                    value=f"{len(ssids)} network(s) visible",
                    confidence=Confidence.HIGH,
                    sources=[DataSource(name="netsh:networks", raw_value=len(ssids))],
                ),
            )
        except Exception:
            pass

    def _read_bluetooth(self, result: ModuleResult) -> None:
        """Query Bluetooth controllers via WMI Win32_PnPEntity."""
        bt_devices = safe_wmi_query(
            "Win32_PnPEntity",
            fields=["Name", "PNPClass", "Manufacturer", "Status"],
            where="PNPClass = 'Bluetooth'",
        )

        # Find the primary radio controller (Adapter)
        controller_name = None
        for dev in bt_devices:
            name = dev.get("Name") or ""
            if any(k in name.lower() for k in ("adapter", "radio", "controller", "wireless")):
                controller_name = name
                break

        if not controller_name and bt_devices:
            controller_name = bt_devices[0].get("Name")

        if controller_name:
            result.add_reading(
                "bluetooth_adapter",
                VerifiedValue(
                    value=controller_name,
                    confidence=Confidence.HIGH,
                    sources=[DataSource(name="WMI:Win32_PnPEntity", raw_value=controller_name)],
                ),
            )
        else:
            result.add_reading(
                "bluetooth_adapter",
                VerifiedValue.unavailable(
                    reason="No Bluetooth adapter radio found",
                ),
            )

    def _read_biometrics(self, result: ModuleResult) -> None:
        """Check for fingerprint scanners or Windows Hello biometric hardware."""
        bio_devices = safe_wmi_query(
            "Win32_PnPEntity",
            fields=["Name", "PNPClass", "Status"],
            where="PNPClass = 'Biometric'",
        )
        if bio_devices:
            bio_names = [d.get("Name") for d in bio_devices if d.get("Name")]
            result.add_reading(
                "biometric_sensor",
                VerifiedValue(
                    value=", ".join(bio_names),
                    confidence=Confidence.HIGH,
                    sources=[DataSource(name="WMI:Win32_PnPEntity", raw_value=bio_names)],
                ),
            )
        else:
            result.add_reading(
                "biometric_sensor",
                VerifiedValue(
                    value="Not Present (No Fingerprint Sensor)",
                    confidence=Confidence.HIGH,
                    sources=[DataSource(name="WMI:Win32_PnPEntity", raw_value="0 devices found")],
                ),
            )

    def _read_audio(self, result: ModuleResult) -> None:
        """Query sound devices and audio input/output endpoints."""
        sound_devs = safe_wmi_query("Win32_SoundDevice", fields=["Name", "Status", "Manufacturer"])
        codecs = [s.get("Name") for s in sound_devs if s.get("Name") and s.get("Status") == "OK"]

        # QtMultimedia devices
        qt_mics: list[str] = []
        qt_speakers: list[str] = []
        try:
            import PySide6.QtMultimedia as mm
            qt_mics = [d.description() for d in mm.QMediaDevices.audioInputs() if d.description()]
            qt_speakers = [d.description() for d in mm.QMediaDevices.audioOutputs() if d.description()]
        except Exception as e:
            logger.debug("QtMultimedia audio query failed: %s", e)

        # Primary audio codec
        if codecs:
            result.add_reading(
                "audio_controller",
                VerifiedValue(
                    value=", ".join(codecs),
                    confidence=Confidence.HIGH,
                    sources=[DataSource(name="WMI:Win32_SoundDevice", raw_value=codecs)],
                ),
            )
        else:
            result.add_reading(
                "audio_controller",
                VerifiedValue.unavailable(reason="No audio sound card or codec found"),
            )

        # Input & Output endpoints
        if qt_mics:
            result.add_reading(
                "audio_inputs",
                VerifiedValue(
                    value=f"{len(qt_mics)} detected: {', '.join(qt_mics[:2])}",
                    confidence=Confidence.HIGH,
                    sources=[DataSource(name="QtMultimedia:audioInputs", raw_value=qt_mics)],
                ),
            )
        if qt_speakers:
            result.add_reading(
                "audio_outputs",
                VerifiedValue(
                    value=f"{len(qt_speakers)} detected: {', '.join(qt_speakers[:2])}",
                    confidence=Confidence.HIGH,
                    sources=[DataSource(name="QtMultimedia:audioOutputs", raw_value=qt_speakers)],
                ),
            )

    def _read_cameras(self, result: ModuleResult) -> None:
        """Query webcams and imaging sensors."""
        qt_cameras: list[str] = []
        try:
            import PySide6.QtMultimedia as mm
            qt_cameras = [d.description() for d in mm.QMediaDevices.videoInputs() if d.description()]
        except Exception as e:
            logger.debug("QtMultimedia camera query failed: %s", e)

        wmi_cameras = safe_wmi_query(
            "Win32_PnPEntity",
            fields=["Name", "PNPClass"],
            where="PNPClass = 'Camera' OR PNPClass = 'Image'",
        )
        pnp_cam_names = [c.get("Name") for c in wmi_cameras if c.get("Name")]

        sources: list[DataSource] = []
        if qt_cameras:
            sources.append(DataSource(name="QtMultimedia:videoInputs", raw_value=qt_cameras))
        if pnp_cam_names:
            sources.append(DataSource(name="WMI:Win32_PnPEntity", raw_value=pnp_cam_names))

        if sources:
            primary_cam = qt_cameras[0] if qt_cameras else pnp_cam_names[0]
            result.add_reading(
                "webcam",
                VerifiedValue(
                    value=primary_cam,
                    confidence=Confidence.HIGH if len(sources) >= 2 else Confidence.MEDIUM,
                    sources=sources,
                ),
            )
        else:
            result.add_reading(
                "webcam",
                VerifiedValue.unavailable(reason="No webcam or image capture sensor detected"),
            )

    def _read_input_controllers(self, result: ModuleResult) -> None:
        """Query keyboard and pointing devices."""
        kb_list = safe_wmi_query("Win32_Keyboard", fields=["Name", "Description", "Status"])
        kb_names = [k.get("Description") or k.get("Name") for k in kb_list if k.get("Status") == "OK"]
        if kb_names:
            result.add_reading(
                "keyboard_hardware",
                VerifiedValue(
                    value=f"{len(kb_names)} controller(s): {', '.join(list(dict.fromkeys(kb_names)))}",
                    confidence=Confidence.HIGH,
                    sources=[DataSource(name="WMI:Win32_Keyboard", raw_value=kb_names)],
                ),
            )

        mouse_list = safe_wmi_query("Win32_PointingDevice", fields=["Name", "Description", "Status"])
        mouse_names = [m.get("Description") or m.get("Name") for m in mouse_list if m.get("Status") == "OK"]
        if mouse_names:
            result.add_reading(
                "pointing_hardware",
                VerifiedValue(
                    value=f"{len(mouse_names)} device(s): {', '.join(list(dict.fromkeys(mouse_names)))}",
                    confidence=Confidence.HIGH,
                    sources=[DataSource(name="WMI:Win32_PointingDevice", raw_value=mouse_names)],
                ),
            )

    def _read_usb_controllers(self, result: ModuleResult) -> None:
        """Query USB host controllers and root hubs."""
        usb_ctrls = safe_wmi_query("Win32_USBController", fields=["Name", "Manufacturer", "Status"])
        ctrl_names = [c.get("Name") for c in usb_ctrls if c.get("Name")]
        if ctrl_names:
            result.add_reading(
                "usb_controllers",
                VerifiedValue(
                    value=", ".join(ctrl_names),
                    confidence=Confidence.HIGH,
                    sources=[DataSource(name="WMI:Win32_USBController", raw_value=ctrl_names)],
                ),
            )
        else:
            result.add_reading(
                "usb_controllers",
                VerifiedValue.unavailable(reason="USB Host Controller information not available"),
            )
