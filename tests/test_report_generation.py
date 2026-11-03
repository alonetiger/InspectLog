"""Unit tests for PDF and JSON report exporters."""

import json
import os
import sys
import pytest
from PySide6.QtWidgets import QApplication

from hardwareverify.core.models import Confidence, DataSource, ModuleResult, Status, VerifiedValue
from hardwareverify.infra.config import SellerClaims
from hardwareverify.report.json_exporter import JSONReportExporter
from hardwareverify.report.pdf_generator import PDFReportGenerator
from hardwareverify.ui.widgets.claims_dialog import SellerClaimsDialog


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def test_pdf_report_generator_creates_valid_pdf():
    generator = PDFReportGenerator()

    sys_res = ModuleResult("system_identity", "System Identity", status=Status.PASS, health_score=100)
    sys_res.add_reading("serial_number", VerifiedValue("CND1234567", confidence=Confidence.HIGH))
    sys_res.add_reading("manufacturer", VerifiedValue("HP", confidence=Confidence.HIGH))
    sys_res.add_reading("model", VerifiedValue("HP ProBook 450", confidence=Confidence.HIGH))

    bat_res = ModuleResult("battery", "Battery", status=Status.WARNING, health_score=65)
    bat_res.add_reading("wear_percentage", VerifiedValue(35.0, confidence=Confidence.HIGH))
    bat_res.add_reading("design_capacity", VerifiedValue(45000, confidence=Confidence.HIGH))
    bat_res.add_reading("full_charge_capacity", VerifiedValue(29250, confidence=Confidence.HIGH))

    claims = SellerClaims(cpu_model="Core i5", ram_gb=16, battery_health_pct=90)

    pdf_bytes = generator.generate_pdf([sys_res, bat_res], claims=claims)
    assert len(pdf_bytes) > 1000
    # Must start with PDF magic header
    assert pdf_bytes.startswith(b"%PDF-")


def test_json_report_exporter_valid_schema():
    exporter = JSONReportExporter()

    cpu_res = ModuleResult("cpu", "Processor (CPU)", status=Status.PASS, health_score=100)
    cpu_res.add_reading("cpu_model", VerifiedValue(
        "Intel Core i7-12700H",
        confidence=Confidence.HIGH,
        sources=[DataSource(name="WMI:Win32_Processor", raw_value="i7-12700H")]
    ))

    claims = SellerClaims(cpu_model="Core i7", ram_gb=16)

    json_str = exporter.export_json([cpu_res], claims=claims)
    data = json.loads(json_str)

    assert "app_name" in data
    assert "audit_timestamp" in data
    assert "scoring" in data
    assert "overall_score" in data["scoring"]
    assert "seller_claims_verification" in data
    assert len(data["modules"]) == 1
    assert data["modules"][0]["module_name"] == "cpu"
    assert data["modules"][0]["readings"]["cpu_model"]["confidence"] == "High"


def test_seller_claims_dialog_ui(qapp):
    claims = SellerClaims(cpu_model="Ryzen 7 5800H", ram_gb=16, storage_gb=1000)
    dlg = SellerClaimsDialog(claims)

    assert dlg.txt_cpu.text() == "Ryzen 7 5800H"
    assert dlg.spn_ram.value() == 16
    assert dlg.spn_storage.value() == 1000

    # Modify values and save
    dlg.txt_cpu.setText("Ryzen 9 5900HX")
    dlg.spn_ram.setValue(32)
    dlg._save_claims()

    assert claims.cpu_model == "Ryzen 9 5900HX"
    assert claims.ram_gb == 32.0
