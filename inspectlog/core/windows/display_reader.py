"""Windows Display Reader implementation.

Reads monitor hardware telemetry from WMI (root/wmi and root/cimv2) and Win32 APIs,
performing cross-validation on resolution, refresh rate, and EDID panel characteristics.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import math
import time
from typing import Any

from inspectlog.core.cross_validator import cross_validate, cross_validate_numeric
from inspectlog.core.models import (
    Confidence,
    DataSource,
    ModuleResult,
    Status,
    VerifiedValue,
)
from inspectlog.core.windows.wmi_helpers import safe_wmi_query
from inspectlog.infra.logging import get_logger

logger = get_logger("display_reader")

# Known monitor 3-letter PNP manufacturer IDs
MONITOR_MANUFACTURERS: dict[str, str] = {
    "ACR": "Acer",
    "AOC": "AOC",
    "APP": "Apple",
    "ASU": "ASUS",
    "AUO": "AU Optronics",
    "BNQ": "BenQ",
    "BOE": "BOE Technology",
    "CMN": "Chi Mei Innolux",
    "DEL": "Dell",
    "ENC": "Eizo",
    "GSM": "LG Electronics",
    "HPN": "HP",
    "HWP": "HP",
    "IVM": "Iiyama",
    "LEN": "Lenovo",
    "LGD": "LG Display",
    "MSI": "MSI",
    "NEC": "NEC",
    "PHL": "Philips",
    "SAM": "Samsung",
    "SEC": "Samsung Electronics",
    "SHP": "Sharp",
    "SNY": "Sony",
    "VSC": "ViewSonic",
}

# Video Output Technology mapping (D3DKMDT_VIDEO_OUTPUT_TECHNOLOGY)
VIDEO_OUTPUT_TECH: dict[int, str] = {
    -2147483648: "Internal Display (eDP / Laptop Panel)",
    0: "Other / Unspecified",
    1: "VGA (HD15)",
    2: "S-Video",
    3: "Composite Video",
    4: "Component Video",
    5: "DVI",
    6: "HDMI",
    7: "LVDS (Internal)",
    10: "DisplayPort",
    11: "Embedded DisplayPort (eDP)",
    12: "UDI External",
    14: "Miracast Wireless Display",
}


class DEVMODEW(ctypes.Structure):
    """Win32 DEVMODEW structure for display mode enumeration."""

    _fields_ = [
        ("dmDeviceName", wintypes.WCHAR * 32),
        ("dmSpecVersion", wintypes.WORD),
        ("dmDriverVersion", wintypes.WORD),
        ("dmSize", wintypes.WORD),
        ("dmDriverExtra", wintypes.WORD),
        ("dmFields", wintypes.DWORD),
        ("dmOrientation", wintypes.SHORT),
        ("dmPaperSize", wintypes.SHORT),
        ("dmPaperLength", wintypes.SHORT),
        ("dmPaperWidth", wintypes.SHORT),
        ("dmScale", wintypes.SHORT),
        ("dmCopies", wintypes.SHORT),
        ("dmDefaultSource", wintypes.SHORT),
        ("dmPrintQuality", wintypes.SHORT),
        ("dmColor", wintypes.SHORT),
        ("dmDuplex", wintypes.SHORT),
        ("dmYResolution", wintypes.SHORT),
        ("dmTTOption", wintypes.SHORT),
        ("dmCollate", wintypes.SHORT),
        ("dmFormName", wintypes.WCHAR * 32),
        ("dmLogPixels", wintypes.WORD),
        ("dmBitsPerPel", wintypes.DWORD),
        ("dmPelsWidth", wintypes.DWORD),
        ("dmPelsHeight", wintypes.DWORD),
        ("dmDisplayFlags", wintypes.DWORD),
        ("dmDisplayFrequency", wintypes.DWORD),
    ]


class DisplayReader:
    """Reads display panels, monitors, resolution, refresh rates, and EDID data."""

    def read_display(self) -> list[ModuleResult]:
        """Read all connected display monitors and their capabilities.

        Returns one ModuleResult per detected active monitor.
        """
        logger.info("Reading display devices and EDID telemetry")
        t0 = time.time()

        # 1. Query Win32 APIs for active primary display mode
        api_width, api_height, api_freq, api_bpp = self._read_win32_display_mode()

        # 2. Query WMI root/cimv2 Win32_VideoController
        wmi_video = safe_wmi_query("Win32_VideoController")
        wmi_width = None
        wmi_height = None
        wmi_freq = None
        wmi_bpp = None
        if wmi_video:
            v0 = wmi_video[0]
            wmi_width = v0.get("CurrentHorizontalResolution")
            wmi_height = v0.get("CurrentVerticalResolution")
            wmi_freq = v0.get("CurrentRefreshRate")
            wmi_bpp = v0.get("CurrentBitsPerPixel")

        # 3. Query WMI root/wmi for EDID tables
        wmi_mon_params = safe_wmi_query("WmiMonitorBasicDisplayParams", namespace="root/wmi")
        wmi_mon_ids = safe_wmi_query("WmiMonitorID", namespace="root/wmi")
        wmi_mon_conns = safe_wmi_query("WmiMonitorConnectionParams", namespace="root/wmi")

        # Index EDID records by InstanceName
        params_by_inst: dict[str, dict[str, Any]] = {}
        for p in wmi_mon_params:
            inst = p.get("InstanceName")
            if inst:
                params_by_inst[str(inst).lower()] = p

        ids_by_inst: dict[str, dict[str, Any]] = {}
        for mid in wmi_mon_ids:
            inst = mid.get("InstanceName")
            if inst:
                ids_by_inst[str(inst).lower()] = mid

        conns_by_inst: dict[str, dict[str, Any]] = {}
        for conn in wmi_mon_conns:
            inst = conn.get("InstanceName")
            if inst:
                conns_by_inst[str(inst).lower()] = conn

        results: list[ModuleResult] = []

        # Enumerate unique instances across WMI monitor tables
        instances = list(dict.fromkeys(list(ids_by_inst.keys()) + list(params_by_inst.keys())))

        duration = time.time() - t0

        if not instances:
            # Fallback when root/wmi monitor classes aren't accessible (e.g. basic VM or remote session)
            result = self._build_basic_display_result(
                api_width, api_height, api_freq, api_bpp,
                wmi_width, wmi_height, wmi_freq, wmi_bpp,
                duration=duration,
            )
            return [result]

        for idx, inst in enumerate(instances):
            mid = ids_by_inst.get(inst)
            params = params_by_inst.get(inst)
            conn = conns_by_inst.get(inst)

            result = self._build_edid_display_result(
                idx=idx,
                inst=inst,
                mid=mid,
                params=params,
                conn=conn,
                api_width=api_width,
                api_height=api_height,
                api_freq=api_freq,
                api_bpp=api_bpp,
                wmi_width=wmi_width,
                wmi_height=wmi_height,
                wmi_freq=wmi_freq,
                wmi_bpp=wmi_bpp,
                duration=duration,
            )
            results.append(result)

        return results

    def _read_win32_display_mode(self) -> tuple[int | None, int | None, int | None, int | None]:
        """Read current display settings via EnumDisplaySettingsW."""
        try:
            dm = DEVMODEW()
            dm.dmSize = ctypes.sizeof(DEVMODEW)
            ENUM_CURRENT_SETTINGS = -1
            success = ctypes.windll.user32.EnumDisplaySettingsW(None, ENUM_CURRENT_SETTINGS, ctypes.byref(dm))
            if success:
                return (
                    int(dm.dmPelsWidth) if dm.dmPelsWidth > 0 else None,
                    int(dm.dmPelsHeight) if dm.dmPelsHeight > 0 else None,
                    int(dm.dmDisplayFrequency) if dm.dmDisplayFrequency > 0 else None,
                    int(dm.dmBitsPerPel) if dm.dmBitsPerPel > 0 else None,
                )
        except Exception as e:
            logger.warning("Win32 EnumDisplaySettings failed: %s", e)

        # Fallback to GetSystemMetrics
        try:
            w = ctypes.windll.user32.GetSystemMetrics(0)  # SM_CXSCREEN
            h = ctypes.windll.user32.GetSystemMetrics(1)  # SM_CYSCREEN
            if w > 0 and h > 0:
                return (w, h, None, None)
        except Exception as e:
            logger.warning("Win32 GetSystemMetrics failed: %s", e)

        return (None, None, None, None)

    def _decode_edid_chars(self, raw_tuple: Any) -> str:
        """Decode uint16/uint8 tuple of ASCII characters from WmiMonitorID."""
        if not raw_tuple or not isinstance(raw_tuple, (tuple, list)):
            return ""
        chars = [chr(c) for c in raw_tuple if 32 <= c <= 126]
        return "".join(chars).strip()

    def _build_edid_display_result(
        self,
        idx: int,
        inst: str,
        mid: dict[str, Any] | None,
        params: dict[str, Any] | None,
        conn: dict[str, Any] | None,
        api_width: int | None,
        api_height: int | None,
        api_freq: int | None,
        api_bpp: int | None,
        wmi_width: int | None,
        wmi_height: int | None,
        wmi_freq: int | None,
        wmi_bpp: int | None,
        duration: float,
    ) -> ModuleResult:
        """Build ModuleResult for a monitor identified via EDID tables."""
        mfg_code = ""
        prod_code = ""
        serial_id = ""
        friendly_name = ""
        mfg_year = None
        mfg_week = None

        if mid:
            mfg_code = self._decode_edid_chars(mid.get("ManufacturerName"))
            prod_code = self._decode_edid_chars(mid.get("ProductCodeID"))
            serial_id = self._decode_edid_chars(mid.get("SerialNumberID"))
            friendly_name = self._decode_edid_chars(mid.get("UserFriendlyName"))
            mfg_year = mid.get("YearOfManufacture")
            mfg_week = mid.get("WeekOfManufacture")

        mfg_brand = MONITOR_MANUFACTURERS.get(mfg_code.upper(), mfg_code if mfg_code else "Generic")
        display_label = friendly_name or (f"{mfg_brand} {prod_code}".strip() if prod_code else f"Display {idx + 1}")

        result = ModuleResult(
            module_name="display",
            display_name=f"Display: {display_label}",
            status=Status.PASS,
            icon="🖥️",
            health_score=100,
            is_applicable=True,
        )

        # 1. Model / Manufacturer
        full_model = f"{mfg_brand} ({mfg_code} {prod_code})".strip() if mfg_code else display_label
        result.add_reading(
            "display_model",
            VerifiedValue(
                value=full_model,
                confidence=Confidence.HIGH if mfg_code else Confidence.MEDIUM,
                sources=[
                    DataSource(name="WMI:WmiMonitorID", raw_value=f"{mfg_code} {prod_code}"),
                ],
            ),
        )

        # 2. Panel Size (Diagonal Inches)
        if params:
            h_cm = params.get("MaxHorizontalImageSize")
            v_cm = params.get("MaxVerticalImageSize")
            if h_cm and v_cm and h_cm > 0 and v_cm > 0:
                diag_cm = math.sqrt(h_cm**2 + v_cm**2)
                diag_in = diag_cm / 2.54
                panel_size_str = f'{diag_in:.1f}" ({h_cm} x {v_cm} cm)'
                result.add_reading(
                    "panel_size",
                    VerifiedValue(
                        value=panel_size_str,
                        confidence=Confidence.HIGH,
                        sources=[
                            DataSource(
                                name="WMI:WmiMonitorBasicDisplayParams",
                                raw_value=f"{h_cm}cm x {v_cm}cm",
                            )
                        ],
                    ),
                )
        if "panel_size" not in result.readings:
            result.add_reading(
                "panel_size",
                VerifiedValue.unavailable(
                    reason="Driver did not expose physical dimensions in EDID table",
                    sources=[],
                ),
            )

        # 3. Resolution (Cross-check WMI vs Win32 API)
        res_sources: list[DataSource] = []
        res_str = None
        wmi_res_str = None
        if api_width and api_height:
            res_str = f"{api_width} x {api_height}"
            res_sources.append(DataSource(name="Win32:EnumDisplaySettings", raw_value=res_str))
        if wmi_width and wmi_height:
            wmi_res_str = f"{wmi_width} x {wmi_height}"
            res_sources.append(DataSource(name="WMI:Win32_VideoController", raw_value=wmi_res_str))

        if len(res_sources) >= 2:
            res_match = (api_width == wmi_width and api_height == wmi_height)
            result.add_reading(
                "resolution",
                VerifiedValue(
                    value=res_str or wmi_res_str,
                    confidence=Confidence.HIGH if res_match else Confidence.LOW,
                    sources=res_sources,
                ),
            )
            if not res_match:
                result.add_warning("Resolution mismatch between Win32 display settings and WMI")
        elif len(res_sources) == 1:
            result.add_reading(
                "resolution",
                VerifiedValue(
                    value=res_sources[0].raw_value,
                    confidence=Confidence.MEDIUM,
                    sources=res_sources,
                ),
            )
        else:
            result.add_reading(
                "resolution",
                VerifiedValue.unavailable(
                    reason="Current display resolution could not be queried",
                ),
            )

        # 4. Refresh Rate (Cross-check)
        freq_sources: list[DataSource] = []
        if api_freq and api_freq > 0:
            freq_sources.append(DataSource(name="Win32:EnumDisplaySettings", raw_value=f"{api_freq} Hz"))
        if wmi_freq and wmi_freq > 0:
            freq_sources.append(DataSource(name="WMI:Win32_VideoController", raw_value=f"{wmi_freq} Hz"))

        if len(freq_sources) >= 2:
            freq_match = (api_freq == wmi_freq)
            result.add_reading(
                "refresh_rate",
                VerifiedValue(
                    value=f"{api_freq} Hz",
                    confidence=Confidence.HIGH if freq_match else Confidence.LOW,
                    sources=freq_sources,
                ),
            )
        elif len(freq_sources) == 1:
            result.add_reading(
                "refresh_rate",
                VerifiedValue(
                    value=freq_sources[0].raw_value,
                    confidence=Confidence.MEDIUM,
                    sources=freq_sources,
                ),
            )
        else:
            result.add_reading(
                "refresh_rate",
                VerifiedValue.unavailable(
                    reason="Refresh rate could not be read",
                ),
            )

        # 5. Color Depth
        bpp_val = api_bpp or wmi_bpp
        if bpp_val:
            result.add_reading(
                "color_depth",
                VerifiedValue(
                    value=f"{bpp_val}-bit Color",
                    confidence=Confidence.MEDIUM,
                    sources=[
                        DataSource(
                            name="Win32:EnumDisplaySettings" if api_bpp else "WMI:Win32_VideoController",
                            raw_value=f"{bpp_val} bpp",
                        )
                    ],
                ),
            )

        # 6. Connection / Bus Type
        if conn:
            vot = conn.get("VideoOutputTechnology")
            if vot is not None:
                conn_name = VIDEO_OUTPUT_TECH.get(vot, f"Output Type #{vot}")
                result.add_reading(
                    "connection_type",
                    VerifiedValue(
                        value=conn_name,
                        confidence=Confidence.HIGH,
                        sources=[
                            DataSource(
                                name="WMI:WmiMonitorConnectionParams",
                                raw_value=f"VideoOutputTechnology={vot}",
                            )
                        ],
                    ),
                )

        # 7. Manufacture Date
        if mfg_year and mfg_year > 1990:
            date_str = f"Year {mfg_year}"
            if mfg_week and 1 <= mfg_week <= 53:
                date_str = f"Week {mfg_week}, {mfg_year}"
            result.add_reading(
                "manufacture_date",
                VerifiedValue(
                    value=date_str,
                    confidence=Confidence.HIGH,
                    sources=[
                        DataSource(
                            name="WMI:WmiMonitorID",
                            raw_value=f"Year={mfg_year}, Week={mfg_week}",
                        )
                    ],
                ),
            )

        # 8. Interactive Pixel & Bleed Test Status
        result.add_reading(
            "pixel_defect_test",
            VerifiedValue(
                value="Not Tested (Click 'Run Test' below)",
                confidence=Confidence.MEDIUM,
                sources=[DataSource(name="DisplayTestSequence", raw_value="Not executed yet")],
            ),
        )

        result.finalize(duration)
        return result

    def _build_basic_display_result(
        self,
        api_width: int | None,
        api_height: int | None,
        api_freq: int | None,
        api_bpp: int | None,
        wmi_width: int | None,
        wmi_height: int | None,
        wmi_freq: int | None,
        wmi_bpp: int | None,
        duration: float,
    ) -> ModuleResult:
        """Fallback ModuleResult when EDID is unavailable."""
        result = ModuleResult(
            module_name="display",
            display_name="Display: Primary Monitor",
            status=Status.PASS,
            icon="🖥️",
            health_score=100,
            is_applicable=True,
        )

        width = api_width or wmi_width
        height = api_height or wmi_height
        if width and height:
            result.add_reading(
                "resolution",
                VerifiedValue(
                    value=f"{width} x {height}",
                    confidence=Confidence.MEDIUM,
                    sources=[
                        DataSource(
                            name="Win32:EnumDisplaySettings" if api_width else "WMI:Win32_VideoController",
                            raw_value=f"{width} x {height}",
                        )
                    ],
                ),
            )

        freq = api_freq or wmi_freq
        if freq:
            result.add_reading(
                "refresh_rate",
                VerifiedValue(
                    value=f"{freq} Hz",
                    confidence=Confidence.MEDIUM,
                    sources=[DataSource(name="DisplaySettings", raw_value=f"{freq} Hz")],
                ),
            )

        result.add_reading(
            "pixel_defect_test",
            VerifiedValue(
                value="Not Tested (Click 'Run Test' below)",
                confidence=Confidence.MEDIUM,
                sources=[DataSource(name="DisplayTestSequence", raw_value="Not executed yet")],
            ),
        )

        result.finalize(duration)
        return result
