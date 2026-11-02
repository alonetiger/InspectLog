"""Windows System Identity hardware reader."""

from __future__ import annotations

from datetime import datetime
import platform
import time

from hardwareverify.constants import FAKE_SERIALS
from hardwareverify.core.cross_validator import cross_validate
from hardwareverify.core.models import (
    Confidence,
    DataSource,
    ModuleResult,
    Status,
    VerifiedValue,
)
from hardwareverify.core.windows.wmi_helpers import safe_wmi_query, safe_wmi_value
from hardwareverify.infra.logging import get_logger

logger = get_logger("system_reader")


def parse_wmi_date(wmi_date_str: str | None) -> tuple[str | None, datetime | None]:
    """Parse WMI CIM_DATETIME string (e.g. '20231015000000.000000+000') into formatted date."""
    if not wmi_date_str:
        return None, None
    clean = str(wmi_date_str).strip()
    if len(clean) >= 8 and clean[:8].isdigit():
        try:
            dt = datetime.strptime(clean[:8], "%Y%m%d")
            return dt.strftime("%Y-%m-%d"), dt
        except ValueError:
            pass
    # If already a human string like '10/15/2023'
    return clean, None


class SystemReader:
    """Reads system identification, motherboard, BIOS, OS, and activation status."""

    def read_system_identity(self) -> ModuleResult:
        """Collect all system identity information and return a ModuleResult."""
        start_time = time.perf_counter()
        result = ModuleResult(
            module_name="system_identity",
            display_name="System Identity",
            icon="🖥️",
        )

        # 1. Computer System (Manufacturer & Model)
        cs_rows = safe_wmi_query(
            "Win32_ComputerSystem",
            fields=["Manufacturer", "Model", "SystemType"],
        )
        if cs_rows:
            raw_mfg = cs_rows[0].get("Manufacturer")
            mfg = str(raw_mfg).strip() if raw_mfg else None
            result.add_reading(
                "manufacturer",
                VerifiedValue.from_single(
                    value=mfg,
                    source_name="WMI:Win32_ComputerSystem.Manufacturer",
                    raw_value=raw_mfg,
                ) if mfg else VerifiedValue.unavailable(
                    reason="Manufacturer field is empty in BIOS/WMI",
                    sources=[DataSource("WMI:Win32_ComputerSystem.Manufacturer", raw_mfg)],
                ),
            )

            raw_model = cs_rows[0].get("Model")
            model = str(raw_model).strip() if raw_model else None
            result.add_reading(
                "model",
                VerifiedValue.from_single(
                    value=model,
                    source_name="WMI:Win32_ComputerSystem.Model",
                    raw_value=raw_model,
                ) if model else VerifiedValue.unavailable(
                    reason="Model field is empty in BIOS/WMI",
                    sources=[DataSource("WMI:Win32_ComputerSystem.Model", raw_model)],
                ),
            )
        else:
            result.add_reading(
                "manufacturer",
                VerifiedValue.unavailable("WMI query for Win32_ComputerSystem failed"),
            )
            result.add_reading(
                "model",
                VerifiedValue.unavailable("WMI query for Win32_ComputerSystem failed"),
            )

        # 2. BIOS & Serial Number cross-validation
        bios_rows = safe_wmi_query(
            "Win32_BIOS",
            fields=["SerialNumber", "SMBIOSBIOSVersion", "Version", "ReleaseDate"],
        )
        enclosure_rows = safe_wmi_query(
            "Win32_SystemEnclosure",
            fields=["SerialNumber"],
        )

        bios_serial = bios_rows[0].get("SerialNumber") if bios_rows else None
        enclosure_serial = enclosure_rows[0].get("SerialNumber") if enclosure_rows else None

        serial_readings = [
            ("WMI:Win32_BIOS.SerialNumber", str(bios_serial).strip() if bios_serial else None),
            ("WMI:Win32_SystemEnclosure.SerialNumber", str(enclosure_serial).strip() if enclosure_serial else None),
        ]
        serial_val = cross_validate(serial_readings)

        # Check for fake/placeholder serial
        if serial_val.is_available and serial_val.value:
            norm_serial = str(serial_val.value).strip().lower()
            if norm_serial in FAKE_SERIALS or "to be filled" in norm_serial:
                result.add_warning(
                    f"Suspicious / placeholder serial number detected: '{serial_val.value}'. "
                    f"Common on custom builds, refurbished, or modified hardware."
                )
                result.deduct_score(15)
                # Lower confidence due to invalid serial
                serial_val.confidence = Confidence.LOW
        else:
            result.add_warning("Serial number could not be determined.")
            result.deduct_score(10)

        result.add_reading("serial_number", serial_val)

        # BIOS Version & Date
        if bios_rows:
            bios_ver = bios_rows[0].get("SMBIOSBIOSVersion") or bios_rows[0].get("Version")
            result.add_reading(
                "bios_version",
                VerifiedValue.from_single(
                    value=str(bios_ver).strip() if bios_ver else None,
                    source_name="WMI:Win32_BIOS.SMBIOSBIOSVersion",
                    raw_value=bios_ver,
                ) if bios_ver else VerifiedValue.unavailable(
                    reason="BIOS Version not reported by Win32_BIOS",
                    sources=[DataSource("WMI:Win32_BIOS", bios_rows[0])],
                ),
            )

            raw_date = bios_rows[0].get("ReleaseDate")
            date_str, dt_obj = parse_wmi_date(raw_date)
            if date_str:
                result.add_reading(
                    "bios_date",
                    VerifiedValue.from_single(
                        value=date_str,
                        source_name="WMI:Win32_BIOS.ReleaseDate",
                        raw_value=raw_date,
                    ),
                )
                if dt_obj:
                    age_years = (datetime.now() - dt_obj).days / 365.25
                    if age_years > 10.0:
                        result.add_warning(
                            f"BIOS release date ({date_str}) is over {int(age_years)} years old. "
                            f"Hardware may be very old or BIOS severely outdated."
                        )
                        result.deduct_score(5)
            else:
                result.add_reading(
                    "bios_date",
                    VerifiedValue.unavailable(
                        reason="BIOS release date could not be parsed",
                        sources=[DataSource("WMI:Win32_BIOS.ReleaseDate", raw_date)],
                    ),
                )
        else:
            result.add_reading("bios_version", VerifiedValue.unavailable("Win32_BIOS query returned no records"))
            result.add_reading("bios_date", VerifiedValue.unavailable("Win32_BIOS query returned no records"))

        # 3. Motherboard (Win32_BaseBoard)
        bb_rows = safe_wmi_query("Win32_BaseBoard", fields=["Manufacturer", "Product", "SerialNumber"])
        if bb_rows:
            bb_mfg = bb_rows[0].get("Manufacturer") or ""
            bb_prod = bb_rows[0].get("Product") or ""
            bb_name = f"{bb_mfg} {bb_prod}".strip() or None
            result.add_reading(
                "motherboard",
                VerifiedValue.from_single(
                    value=bb_name,
                    source_name="WMI:Win32_BaseBoard",
                    raw_value=bb_rows[0],
                ) if bb_name else VerifiedValue.unavailable("Motherboard info empty in WMI"),
            )
        else:
            result.add_reading(
                "motherboard",
                VerifiedValue.unavailable("Win32_BaseBoard query returned no records"),
            )

        # 4. OS Build
        os_rows = safe_wmi_query("Win32_OperatingSystem", fields=["Caption", "Version", "BuildNumber"])
        plat_ver = platform.version()
        if os_rows:
            caption = str(os_rows[0].get("Caption") or "").strip()
            version = str(os_rows[0].get("Version") or "").strip()
            build = str(os_rows[0].get("BuildNumber") or "").strip()
            os_summary = f"{caption} (Build {build})".strip() or version
            result.add_reading(
                "os_build",
                VerifiedValue(
                    value=os_summary,
                    sources=[
                        DataSource("WMI:Win32_OperatingSystem", os_rows[0]),
                        DataSource("platform.version()", plat_ver),
                    ],
                    confidence=Confidence.HIGH if build in plat_ver or version in plat_ver else Confidence.MEDIUM,
                ),
            )
        else:
            result.add_reading(
                "os_build",
                VerifiedValue.from_single(
                    value=f"Windows ({platform.platform()})",
                    source_name="platform.platform()",
                ),
            )

        # 5. Windows Activation Status
        # Query SoftwareLicensingProduct for Windows (ApplicationID 55c92734-d682-4d71-983e-d6ec3f16059f)
        try:
            lic_rows = safe_wmi_query(
                "SoftwareLicensingProduct",
                fields=["Name", "LicenseStatus", "PartialProductKey"],
                where="ApplicationID='55c92734-d682-4d71-983e-d6ec3f16059f' AND PartialProductKey IS NOT NULL",
            )
            # LicenseStatus values: 1 = Licensed, 2 = OOBGrace, 3 = OOTGrace, 4 = NonGenuineGrace, 5 = Notification
            is_licensed = False
            status_desc = "Not Activated"
            if lic_rows:
                for row in lic_rows:
                    status_code = row.get("LicenseStatus")
                    if status_code == 1:
                        is_licensed = True
                        status_desc = "Activated (Licensed)"
                        break
                    elif status_code in (2, 3):
                        status_desc = "Grace Period (Temporary)"
                    elif status_code == 4:
                        status_desc = "Non-Genuine Grace Period"
                    elif status_code == 5:
                        status_desc = "Notification (Unactivated)"

            result.add_reading(
                "windows_activation",
                VerifiedValue.from_single(
                    value=status_desc,
                    source_name="WMI:SoftwareLicensingProduct",
                    raw_value=lic_rows if lic_rows else None,
                ),
            )

            if not is_licensed:
                result.add_warning("Windows is not genuinely activated on this machine.")
                result.deduct_score(10)
        except Exception as e:
            logger.warning("Failed to check Windows activation: %s", e)
            result.add_reading(
                "windows_activation",
                VerifiedValue.unavailable(f"Could not query licensing status: {e}"),
            )

        duration = time.perf_counter() - start_time
        result.finalize(duration)
        return result
