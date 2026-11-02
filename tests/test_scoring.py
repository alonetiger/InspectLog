"""Unit tests for HardwareVerify Scoring Engine and Buy Confidence evaluator."""

import pytest

from hardwareverify.core.models import Confidence, DataSource, ModuleResult, Status, VerifiedValue
from hardwareverify.report.scoring import ScoringEngine


def test_scoring_engine_high_confidence():
    """Verify clean system with 100% scores results in HIGH buy confidence."""
    engine = ScoringEngine()

    results = [
        ModuleResult("system_identity", "System Identity", status=Status.PASS, health_score=100),
        ModuleResult("battery", "Battery", status=Status.PASS, health_score=100),
        ModuleResult("storage", "Storage", status=Status.PASS, health_score=100),
        ModuleResult("ram", "RAM", status=Status.PASS, health_score=100),
        ModuleResult("cpu", "CPU", status=Status.PASS, health_score=100),
        ModuleResult("gpu", "GPU", status=Status.PASS, health_score=100),
        ModuleResult("display", "Display", status=Status.PASS, health_score=100),
        ModuleResult("thermals", "Thermals & Fans", status=Status.PASS, health_score=100),
        ModuleResult("security", "Security & Locks", status=Status.PASS, health_score=100),
        ModuleResult("input_io", "Input & Peripherals", status=Status.PASS, health_score=100),
    ]

    summary = engine.evaluate(results)
    assert summary.overall_score == 100
    assert summary.verdict == "HIGH"
    assert "HIGH" in summary.verdict_title
    assert len(summary.red_flags) == 0


def test_scoring_desktop_battery_redistribution():
    """Verify that when battery is not applicable, its 15% weight is redistributed proportionally."""
    engine = ScoringEngine()

    # Laptop with 100% on everything except battery which is not present
    results = [
        ModuleResult("system_identity", "System Identity", status=Status.PASS, health_score=100),
        ModuleResult("battery", "Battery", status=Status.NOT_TESTED, health_score=100, is_applicable=False),
        ModuleResult("storage", "Storage", status=Status.PASS, health_score=80),
        ModuleResult("ram", "RAM", status=Status.PASS, health_score=100),
        ModuleResult("cpu", "CPU", status=Status.PASS, health_score=100),
        ModuleResult("gpu", "GPU", status=Status.PASS, health_score=100),
        ModuleResult("display", "Display", status=Status.PASS, health_score=100),
        ModuleResult("thermals", "Thermals & Fans", status=Status.PASS, health_score=100),
        ModuleResult("security", "Security & Locks", status=Status.PASS, health_score=100),
        ModuleResult("input_io", "Input & Peripherals", status=Status.PASS, health_score=100),
    ]

    summary = engine.evaluate(results)
    assert summary.applicable_modules_count == 9
    assert "battery" not in summary.module_scores
    # Overall score should be close to 95 (only storage is 80, which is weighted ~23.5% after redistribution)
    assert 93 <= summary.overall_score <= 97


def test_scoring_red_flags_synthesis():
    """Verify that severe battery wear and failing storage trigger red flags and negotiation tips."""
    engine = ScoringEngine()

    bat_mod = ModuleResult("battery", "Battery", status=Status.WARNING, health_score=50)
    bat_mod.add_reading("wear_percentage", VerifiedValue(45.0, confidence=Confidence.HIGH))
    bat_mod.add_reading("design_capacity", VerifiedValue(50000, confidence=Confidence.HIGH))
    bat_mod.add_reading("full_charge_capacity", VerifiedValue(27500, confidence=Confidence.HIGH))

    storage_mod = ModuleResult("storage", "Storage", status=Status.FAIL, health_score=20)
    storage_mod.add_reading("smart_status", VerifiedValue("Failing", confidence=Confidence.HIGH))
    storage_mod.add_reading("power_on_hours", VerifiedValue(25000, confidence=Confidence.HIGH))
    storage_mod.add_reading("reallocated_sectors", VerifiedValue(128, confidence=Confidence.HIGH))

    sec_mod = ModuleResult("security", "Security & Locks", status=Status.FAIL, health_score=30)
    sec_mod.add_reading("mdm_enrolled", VerifiedValue("Microsoft Intune Managed", confidence=Confidence.HIGH))

    results = [bat_mod, storage_mod, sec_mod]

    summary = engine.evaluate(results)
    assert summary.verdict == "LOW"
    assert len(summary.red_flags) >= 3
    assert any("45.0% capacity lost" in rf for rf in summary.red_flags)
    assert any("FAILING SMART" in rf for rf in summary.red_flags)
    assert any("MDM" in rf for rf in summary.red_flags)
    assert any("negotiate" in r.lower() or "replace" in r.lower() for r in summary.recommendations)
