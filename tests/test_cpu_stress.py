"""Unit tests for the CPU and GPU stress tests."""

import pytest
from unittest.mock import patch

from hardwareverify.tests_engine.stress.cpu_stress import run_cpu_stress_test
from hardwareverify.tests_engine.stress.gpu_stress import run_gpu_stress_test


def test_cpu_stress_short_run():
    # Run a short 2-second test
    res = run_cpu_stress_test(duration_s=2)

    assert "verdict" in res
    assert res["error_message"] is None
    assert len(res["samples"]) >= 1
    assert res["emergency_aborted"] is False


def test_cpu_stress_cancellation():
    res = run_cpu_stress_test(
        duration_s=10,
        cancel_check=lambda: True,
    )
    assert "cancelled" in (res.get("error_message") or "").lower()


def test_gpu_stress_short_run():
    res = run_gpu_stress_test(duration_s=2)

    assert "verdict" in res
    assert res["error_message"] is None
    assert res["crashes_detected"] == 0
