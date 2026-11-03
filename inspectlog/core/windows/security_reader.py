"""Windows Security, Secure Boot, TPM, MDM enrollment, and Enterprise locks reader."""

from __future__ import annotations

import subprocess
import time
import winreg

from inspectlog.core.cross_validator import cross_validate
from inspectlog.core.models import (
    Confidence,
    DataSource,
    ModuleResult,
    Status,
    VerifiedValue,
)
from inspectlog.core.windows.wmi_helpers import safe_wmi_query
from inspectlog.infra.logging import get_logger

logger = get_logger("security_reader")


def _check_secure_boot_registry() -> bool | None:
    """Read Secure Boot state from Windows registry."""
    key_path = r"SYSTEM\CurrentControlSet\Control\SecureBoot\State"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as k:
            val, _ = winreg.QueryValueEx(k, "UEFISecureBootEnabled")
            return bool(val == 1)
    except Exception:
        return None


def _check_mdm_enrollments() -> list[str]:
    """Check for active enterprise Mobile Device Management (MDM) enrollments."""
    enrolled_providers: list[str] = []
    key_path = r"SOFTWARE\Microsoft\Enrollments"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as k:
            idx = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(k, idx)
                    idx += 1
                    with winreg.OpenKey(k, subkey_name) as sub:
                        try:
                            provider, _ = winreg.QueryValueEx(sub, "ProviderID")
                            if provider and str(provider).strip():
                                enrolled_providers.append(str(provider))
                        except Exception:
                            pass
                except OSError:
                    break
    except Exception as e:
        logger.debug("MDM check error: %s", e)
    return enrolled_providers


def _check_domain_joined() -> tuple[bool, str]:
    """Check if device is joined to an on-premise Windows Domain or Azure AD."""
    rows = safe_wmi_query("Win32_ComputerSystem", fields=["PartOfDomain", "Domain", "Workgroup"])
    if rows:
        part_of_dom = rows[0].get("PartOfDomain")
        dom_name = rows[0].get("Domain") or ""
        if part_of_dom:
            return True, f"Corporate Domain Joined: {dom_name}"
        return False, f"Workgroup ({rows[0].get('Workgroup') or 'WORKGROUP'})"
    return False, "Standalone / Unknown"


class SecurityReader:
    """Checks device lock states, Secure Boot, TPM chip, MDM enrollment, and corporate management."""

    def read_security(self) -> ModuleResult:
        """Inspect security states and return a ModuleResult."""
        start_time = time.perf_counter()
        result = ModuleResult(
            module_name="security",
            display_name="Security & Locks",
            icon="🔒",
        )

        # 1. Secure Boot
        sec_boot_reg = _check_secure_boot_registry()
        if sec_boot_reg is not None:
            sb_status = "Enabled" if sec_boot_reg else "Disabled"
            result.add_reading(
                "secure_boot",
                VerifiedValue.from_single(
                    value=sb_status,
                    source_name="Registry:UEFISecureBootEnabled",
                    raw_value=sec_boot_reg,
                ),
            )
            if not sec_boot_reg:
                result.add_warning("Secure Boot is Disabled. Recommended to enable in UEFI firmware.")
                result.deduct_score(5)
        else:
            result.add_reading(
                "secure_boot",
                VerifiedValue.unavailable("Secure Boot state could not be read from registry"),
            )

        # 2. TPM (Trusted Platform Module)
        tpm_rows = safe_wmi_query(
            "Win32_Tpm",
            namespace="root/cimv2/Security/MicrosoftTpm",
            fields=["IsActivated_InitialValue", "IsEnabled_InitialValue", "SpecVersion", "ManufacturerVersion"],
        )

        if tpm_rows:
            t = tpm_rows[0]
            spec_ver = str(t.get("SpecVersion") or "Present").strip()
            is_enabled = t.get("IsEnabled_InitialValue", True)
            tpm_desc = f"TPM {spec_ver} (Active)" if is_enabled else f"TPM {spec_ver} (Disabled)"
            result.add_reading(
                "tpm_present",
                VerifiedValue.from_single(
                    value=tpm_desc,
                    source_name="WMI:root/cimv2/Security/MicrosoftTpm:Win32_Tpm",
                    raw_value=t,
                ),
            )
        else:
            result.add_reading(
                "tpm_present",
                VerifiedValue.from_single("Not Detected / Missing", "WMI:MicrosoftTpm"),
            )
            result.add_warning("No active TPM chip detected. Windows 11 features and BitLocker may be unsupported.")
            result.deduct_score(10)

        # 3. MDM / Enterprise Management Enrollment (Critical buyer warning!)
        mdm_providers = _check_mdm_enrollments()
        if mdm_providers:
            provider_list = ", ".join(set(mdm_providers))
            result.add_reading(
                "mdm_enrolled",
                VerifiedValue(
                    value=f"ENROLLED ({provider_list})",
                    sources=[DataSource("Registry:HKLM/SOFTWARE/Microsoft/Enrollments", mdm_providers)],
                    confidence=Confidence.HIGH,
                ),
            )
            result.add_error(
                f"RED FLAG: Device is enrolled in corporate Mobile Device Management ({provider_list})! "
                f"The device may be enterprise-owned, remotely tracked, or subject to remote locking/wiping. "
                f"Ensure the organization removes the device from their MDM tenant before purchase."
            )
            result.deduct_score(40)
        else:
            result.add_reading(
                "mdm_enrolled",
                VerifiedValue.from_single("None (Clean Consumer Device)", "Registry:Enrollments"),
            )

        # 4. Domain Join
        is_dom, dom_desc = _check_domain_joined()
        result.add_reading(
            "domain_joined",
            VerifiedValue.from_single(dom_desc, "WMI:Win32_ComputerSystem.PartOfDomain"),
        )
        if is_dom:
            result.add_warning(f"Device is joined to a corporate domain ({dom_desc}).")
            result.deduct_score(15)

        duration = time.perf_counter() - start_time
        result.finalize(duration)
        return result
