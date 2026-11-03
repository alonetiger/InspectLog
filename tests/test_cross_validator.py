"""Unit tests for the cross-validation engine."""

import pytest
from hardwareverify.core.cross_validator import cross_validate, cross_validate_numeric
from hardwareverify.core.models import Confidence


def test_cross_validate_single_source():
    readings = [("Source1", "Model ABC")]
    result = cross_validate(readings)

    assert result.is_available
    assert result.value == "Model ABC"
    assert result.confidence == Confidence.MEDIUM
    assert len(result.sources) == 1


def test_cross_validate_two_agreeing_sources():
    readings = [
        ("Source1", "Model ABC"),
        ("Source2", "model abc"),  # Case insensitive match
    ]
    result = cross_validate(readings)

    assert result.is_available
    assert result.value == "Model ABC"
    assert result.confidence == Confidence.HIGH
    assert len(result.sources) == 2


def test_cross_validate_disagreeing_sources():
    readings = [
        ("Source1", "Model ABC"),
        ("Source2", "Model XYZ"),
    ]
    result = cross_validate(readings)

    assert result.is_available
    assert result.value == "Model ABC"
    assert result.confidence == Confidence.LOW


def test_cross_validate_all_none():
    readings = [
        ("Source1", None),
        ("Source2", None),
    ]
    result = cross_validate(readings)

    assert not result.is_available
    assert result.value is None
    assert result.unavailable_reason is not None


def test_cross_validate_one_none_one_valid():
    readings = [
        ("Source1", None),
        ("Source2", "Valid Value"),
    ]
    result = cross_validate(readings)

    assert result.is_available
    assert result.value == "Valid Value"
    assert result.confidence == Confidence.MEDIUM


def test_cross_validate_numeric_tolerance():
    # 54000 vs 53000 is ~1.85% difference -> within default 5% tolerance
    readings = [
        ("Source1", 54000),
        ("Source2", 53000),
    ]
    result = cross_validate_numeric(readings, tolerance_pct=5.0)

    assert result.is_available
    assert result.value == 54000
    assert result.confidence == Confidence.HIGH


def test_cross_validate_numeric_exceeds_tolerance():
    # 54000 vs 45000 is ~16.6% difference -> exceeds 5% tolerance
    readings = [
        ("Source1", 54000),
        ("Source2", 45000),
    ]
    result = cross_validate_numeric(readings, tolerance_pct=5.0)

    assert result.is_available
    assert result.confidence == Confidence.LOW
