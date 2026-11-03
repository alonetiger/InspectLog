"""Unit tests for seller advertised claims matching engine."""

import pytest

from inspectlog.core.models import Confidence, ModuleResult, Status, VerifiedValue
from inspectlog.infra.config import SellerClaims
from inspectlog.report.claims_matcher import ClaimsMatcher


def test_claims_matcher_all_match():
    matcher = ClaimsMatcher()

    claims = SellerClaims(
        cpu_model="Intel Core i7-12700H",
        ram_gb=16,
        storage_gb=1000,
        storage_type="NVMe",
        gpu_model="RTX 3060",
        battery_health_pct=85,
        screen_resolution="1920x1080",
        screen_size_inches=15.6,
    )

    cpu_mod = ModuleResult("cpu", "CPU")
    cpu_mod.add_reading("cpu_model", VerifiedValue("12th Gen Intel(R) Core(TM) i7-12700H", confidence=Confidence.HIGH))

    ram_mod = ModuleResult("ram", "RAM")
    ram_mod.add_reading("total_ram", VerifiedValue("16 GB", confidence=Confidence.HIGH))

    storage_mod = ModuleResult("storage", "Storage")
    storage_mod.add_reading("disk_capacity", VerifiedValue("1000.2 GB", confidence=Confidence.HIGH))
    storage_mod.add_reading("media_type", VerifiedValue("NVMe SSD", confidence=Confidence.HIGH))

    gpu_mod = ModuleResult("gpu", "GPU")
    gpu_mod.add_reading("gpu_model", VerifiedValue("NVIDIA GeForce RTX 3060 Laptop GPU", confidence=Confidence.HIGH))

    bat_mod = ModuleResult("battery", "Battery")
    bat_mod.add_reading("wear_percentage", VerifiedValue(12.0, confidence=Confidence.HIGH))  # 88% health

    disp_mod = ModuleResult("display", "Display")
    disp_mod.add_reading("resolution", VerifiedValue("1920 x 1080", confidence=Confidence.HIGH))
    disp_mod.add_reading("panel_size", VerifiedValue('15.6" (34 x 19 cm)', confidence=Confidence.HIGH))

    results = [cpu_mod, ram_mod, storage_mod, gpu_mod, bat_mod, disp_mod]

    report = matcher.compare(claims, results)
    assert report.has_claims
    assert report.all_matched
    assert report.mismatches_count == 0
    assert report.matches_count == 7


def test_claims_matcher_shortfall_mismatches():
    matcher = ClaimsMatcher()

    claims = SellerClaims(
        cpu_model="Intel Core i7-12700H",
        ram_gb=32,
        storage_gb=2000,
        gpu_model="RTX 4080",
        battery_health_pct=95,
    )

    cpu_mod = ModuleResult("cpu", "CPU")
    cpu_mod.add_reading("cpu_model", VerifiedValue("Intel(R) Core(TM) i3-6006U", confidence=Confidence.HIGH))

    ram_mod = ModuleResult("ram", "RAM")
    ram_mod.add_reading("total_ram", VerifiedValue("8 GB", confidence=Confidence.HIGH))

    storage_mod = ModuleResult("storage", "Storage")
    storage_mod.add_reading("disk_capacity", VerifiedValue("240 GB", confidence=Confidence.HIGH))

    gpu_mod = ModuleResult("gpu", "GPU")
    gpu_mod.add_reading("gpu_model", VerifiedValue("Intel HD Graphics 520", confidence=Confidence.HIGH))

    bat_mod = ModuleResult("battery", "Battery")
    bat_mod.add_reading("wear_percentage", VerifiedValue(40.0, confidence=Confidence.HIGH))  # 60% health

    results = [cpu_mod, ram_mod, storage_mod, gpu_mod, bat_mod]

    report = matcher.compare(claims, results)
    assert report.has_claims
    assert not report.all_matched
    assert report.mismatches_count == 5
    assert report.matches_count == 0

    # Verify specific mismatch details
    ram_item = next(it for it in report.items if it.component == "Memory (RAM)")
    assert not ram_item.is_match
    assert "24 GB missing" in ram_item.details

    gpu_item = next(it for it in report.items if it.component == "Graphics (GPU)")
    assert not gpu_item.is_match
    assert "RTX 4080" in gpu_item.details
