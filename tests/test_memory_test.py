"""Unit tests for the memory pattern stress test."""

import pytest
from hardwareverify.tests_engine.stress.memory_test import run_memory_pattern_test


def test_memory_pattern_test_execution():
    # Run test on 8MB chunk for quick unit test verification
    res = run_memory_pattern_test(test_size_mb=8)

    assert res["passed"] is True
    assert res["error_count"] == 0
    assert "Checkerboard" in res["patterns_tested"]
    assert "Walking Ones" in res["patterns_tested"]
    assert "Walking Zeros" in res["patterns_tested"]
    assert "Pseudo-Random" in res["patterns_tested"]


def test_memory_pattern_test_cancellation():
    res = run_memory_pattern_test(
        test_size_mb=16,
        cancel_check=lambda: True,
    )
    assert res["error_count"] == 0
