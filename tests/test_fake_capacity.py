"""Unit tests for the counterfeit fake-capacity storage detection test."""

import os
import tempfile
import pytest

from hardwareverify.tests_engine.benchmarks.fake_capacity import (
    generate_test_block,
    run_fake_capacity_check,
    verify_test_block,
)


def test_block_generation_and_verification():
    block0 = generate_test_block(seed=0, length=4096)
    block1 = generate_test_block(seed=1, length=4096)

    assert len(block0) == 4096
    assert block0 != block1
    assert verify_test_block(block0, seed=0) is True
    assert verify_test_block(block0, seed=1) is False


def test_fake_capacity_check_genuine_drive():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Run test with 16MB container
        res = run_fake_capacity_check(target_dir=tmpdir, test_size_mb=16)

        assert res["is_genuine"] is True
        assert res["errors_detected"] == 0
        assert res["blocks_tested"] == 8
        assert res["error_message"] is None

        # Verify temp file was cleaned up
        assert not os.path.exists(res["test_file_path"])


def test_fake_capacity_check_cancellation():
    with tempfile.TemporaryDirectory() as tmpdir:
        res = run_fake_capacity_check(
            target_dir=tmpdir,
            test_size_mb=32,
            cancel_check=lambda: True,  # Immediate cancellation
        )
        assert "cancelled" in (res.get("error_message") or "").lower()
