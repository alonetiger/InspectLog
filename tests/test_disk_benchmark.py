"""Unit tests for the safe disk performance benchmark."""

import os
import tempfile
import pytest

from hardwareverify.tests_engine.benchmarks.disk_benchmark import run_disk_benchmark


def test_disk_benchmark_execution():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Run a small 16MB benchmark for unit test speed
        res = run_disk_benchmark(target_dir=tmpdir, size_mb=16)

        assert res["seq_write_mb_s"] > 0
        assert res["seq_read_mb_s"] > 0
        assert res["random_4k_read_iops"] > 0
        assert res["random_4k_write_iops"] > 0
        assert res["error_message"] is None


def test_disk_benchmark_cancellation():
    with tempfile.TemporaryDirectory() as tmpdir:
        res = run_disk_benchmark(
            target_dir=tmpdir,
            size_mb=32,
            cancel_check=lambda: True,
        )
        assert "cancelled" in (res.get("error_message") or "").lower()
