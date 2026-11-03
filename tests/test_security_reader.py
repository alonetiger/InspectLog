"""Unit tests for the Security & Locks reader (Secure Boot, TPM, MDM)."""

from unittest.mock import patch
import pytest

from hardwareverify.core.models import Status
from hardwareverify.core.windows.security_reader import SecurityReader


def test_security_reader_clean_pc(load_fixture):
    data = load_fixture("wmi_security_sample.json")
    tpm_data = data["Win32_Tpm"]
    cs_data = data["Win32_ComputerSystem"]

    def _mock_query(cls, **kwargs):
        if cls == "Win32_Tpm":
            return tpm_data
        elif cls == "Win32_ComputerSystem":
            return cs_data
        return []

    reader = SecurityReader()

    with patch("hardwareverify.core.windows.security_reader.safe_wmi_query", side_effect=_mock_query), \
         patch("hardwareverify.core.windows.security_reader._check_secure_boot_registry", return_value=True), \
         patch("hardwareverify.core.windows.security_reader._check_mdm_enrollments", return_value=[]):
        result = reader.read_security()

    assert result.module_name == "security"
    assert result.status == Status.PASS
    assert result.health_score == 100
    assert result.readings["secure_boot"].value == "Enabled"
    assert "TPM 2.0" in result.readings["tpm_present"].value
    assert "Clean Consumer Device" in result.readings["mdm_enrolled"].value


def test_security_reader_mdm_enrolled(load_fixture):
    # Corporate device enrolled in Intune / Workspace ONE
    reader = SecurityReader()

    with patch("hardwareverify.core.windows.security_reader.safe_wmi_query", return_value=[]), \
         patch("hardwareverify.core.windows.security_reader._check_secure_boot_registry", return_value=True), \
         patch("hardwareverify.core.windows.security_reader._check_mdm_enrollments", return_value=["MS DM Server (Intune)"]):
        result = reader.read_security()

    assert result.status == Status.FAIL
    assert any("RED FLAG" in err and "MDM" in err for err in result.errors)
    assert result.health_score < 70
