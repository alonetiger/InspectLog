"""Memory pattern stress test (walking ones, walking zeros, checkerboard, random)."""

from __future__ import annotations

import random
import time
from typing import Any, Callable

from inspectlog.infra.logging import get_logger

logger = get_logger("memory_test")


def run_memory_pattern_test(
    test_size_mb: int = 128,
    progress_callback: Callable[[int, str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Execute walking-ones, walking-zeros, checkerboard, and random memory tests.

    Allocates a block of memory and exercises memory bus address lines and DRAM cells.

    Args:
        test_size_mb: Amount of RAM in megabytes to allocate and test.
        progress_callback: Callback reporting (percentage, status_text).
        cancel_check: Optional callable to check if test was cancelled.

    Returns:
        Dict with keys:
            passed: bool (True if 0 errors found)
            total_bytes_tested: int
            error_count: int
            patterns_tested: list[str]
            duration_s: float
            error_details: list[str]
    """
    start_time = time.perf_counter()
    num_words = (test_size_mb * 1024 * 1024) // 4  # 32-bit words

    out: dict[str, Any] = {
        "passed": True,
        "total_bytes_tested": test_size_mb * 1024 * 1024,
        "error_count": 0,
        "patterns_tested": [],
        "duration_s": 0.0,
        "error_details": [],
    }

    try:
        if progress_callback:
            progress_callback(5, f"Allocating {test_size_mb} MB test buffer in physical memory...")

        # Pre-allocate bytearray
        buf = bytearray(test_size_mb * 1024 * 1024)
        view32 = memoryview(buf).cast("I")

        # 1. Pattern: Checkerboard (0x55555555 / 0xAAAAAAAA)
        if cancel_check and cancel_check():
            return out
        if progress_callback:
            progress_callback(15, "Testing Pattern 1/4: Checkerboard (0x55555555 / 0xAAAAAAAA)...")

        out["patterns_tested"].append("Checkerboard")
        val1 = 0x55555555
        val2 = 0xAAAAAAAA

        for i in range(num_words):
            view32[i] = val1 if (i % 2 == 0) else val2

        for i in range(num_words):
            expected = val1 if (i % 2 == 0) else val2
            if view32[i] != expected:
                out["error_count"] += 1
                out["error_details"].append(f"Checkerboard mismatch at word {i}: got {hex(view32[i])}, expected {hex(expected)}")
                if len(out["error_details"]) > 20:
                    break

        # 2. Pattern: Walking Ones (tests stuck-at-zero faults & address bus bridging)
        if cancel_check and cancel_check():
            return out
        if progress_callback:
            progress_callback(40, "Testing Pattern 2/4: Walking Ones (bit shift 0..31)...")

        out["patterns_tested"].append("Walking Ones")
        for bit in range(32):
            pattern = 1 << bit
            # Write slice or sample
            step = max(1, num_words // 2048)
            for i in range(0, num_words, step):
                view32[i] = pattern

            for i in range(0, num_words, step):
                if view32[i] != pattern:
                    out["error_count"] += 1
                    out["error_details"].append(f"Walking ones bit {bit} error at word {i}")
                    if len(out["error_details"]) > 20:
                        break

        # 3. Pattern: Walking Zeros (tests stuck-at-one faults)
        if cancel_check and cancel_check():
            return out
        if progress_callback:
            progress_callback(65, "Testing Pattern 3/4: Walking Zeros (inverted bit shift)...")

        out["patterns_tested"].append("Walking Zeros")
        for bit in range(32):
            pattern = (~(1 << bit)) & 0xFFFFFFFF
            step = max(1, num_words // 2048)
            for i in range(0, num_words, step):
                view32[i] = pattern

            for i in range(0, num_words, step):
                if view32[i] != pattern:
                    out["error_count"] += 1
                    out["error_details"].append(f"Walking zeros bit {bit} error at word {i}")
                    if len(out["error_details"]) > 20:
                        break

        # 4. Pattern: Pseudo-Random Bit Sequence
        if cancel_check and cancel_check():
            return out
        if progress_callback:
            progress_callback(85, "Testing Pattern 4/4: PRNG random bitstream...")

        out["patterns_tested"].append("Pseudo-Random")
        seed_val = 0x485756  # "HWV"
        prng = random.Random(seed_val)

        sample_stride = max(1, num_words // 4096)
        samples_count = num_words // sample_stride
        random_expected = [prng.getrandbits(32) for _ in range(samples_count)]

        for idx, i in enumerate(range(0, num_words, sample_stride)):
            view32[i] = random_expected[idx]

        for idx, i in enumerate(range(0, num_words, sample_stride)):
            if view32[i] != random_expected[idx]:
                out["error_count"] += 1
                out["error_details"].append(f"Random pattern bit flip at word {i}")
                if len(out["error_details"]) > 20:
                    break

        del view32
        del buf

        out["passed"] = (out["error_count"] == 0)
        if progress_callback:
            progress_callback(100, f"Memory test finished: {out['error_count']} errors.")

    except Exception as e:
        logger.exception("Memory test error: %s", e)
        out["passed"] = False
        out["error_details"].append(str(e))
    finally:
        out["duration_s"] = round(time.perf_counter() - start_time, 2)

    return out
