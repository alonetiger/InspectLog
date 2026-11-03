"""Safe disk performance and throughput benchmark."""

from __future__ import annotations

import os
import random
import tempfile
import time
from typing import Any, Callable

from inspectlog.infra.cleanup import cleanup_manager
from inspectlog.infra.logging import get_logger

logger = get_logger("disk_benchmark")

CHUNK_SIZE = 1024 * 1024  # 1 MB chunk for sequential test
BLOCK_4K = 4 * 1024       # 4 KB chunk for random test


def run_disk_benchmark(
    target_dir: str | None = None,
    size_mb: int = 128,
    progress_callback: Callable[[int, str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Execute sequential and random 4K read/write speed benchmark.

    Args:
        target_dir: Target directory on the drive (defaults to system temp).
        size_mb: Size of sequential test file in MB.
        progress_callback: Optional callback for progress reporting.
        cancel_check: Optional callable to check for user cancellation.

    Returns:
        Dict with keys:
            seq_write_mb_s: float
            seq_read_mb_s: float
            random_4k_read_iops: int
            random_4k_write_iops: int
            duration_s: float
            error_message: str | None
    """
    start_total = time.perf_counter()
    target_dir = target_dir or tempfile.gettempdir()
    bench_file = os.path.join(target_dir, f".hwv_bench_{int(time.time()*1000)}.tmp")
    cleanup_manager.register_file(bench_file)

    out: dict[str, Any] = {
        "seq_write_mb_s": 0.0,
        "seq_read_mb_s": 0.0,
        "random_4k_read_iops": 0,
        "random_4k_write_iops": 0,
        "duration_s": 0.0,
        "error_message": None,
    }

    try:
        # Pre-generate 1MB test buffer
        chunk = os.urandom(CHUNK_SIZE)
        total_chunks = max(16, size_mb)

        # 1. Sequential Write Test
        if progress_callback:
            progress_callback(10, f"Measuring sequential write speed ({size_mb} MB)...")

        t0 = time.perf_counter()
        with open(bench_file, "wb") as f:
            fd = f.fileno()
            for i in range(total_chunks):
                if cancel_check and cancel_check():
                    out["error_message"] = "Benchmark cancelled"
                    return out
                f.write(chunk)
                if progress_callback and i % 16 == 0:
                    pct = int(10 + (i / total_chunks) * 25)
                    progress_callback(pct, "Writing benchmark data...")
            f.flush()
            os.fsync(fd)
        write_duration = max(0.001, time.perf_counter() - t0)
        out["seq_write_mb_s"] = round(size_mb / write_duration, 1)

        # 2. Sequential Read Test
        if progress_callback:
            progress_callback(40, f"Measuring sequential read speed ({size_mb} MB)...")

        t0 = time.perf_counter()
        with open(bench_file, "rb") as f:
            for i in range(total_chunks):
                if cancel_check and cancel_check():
                    out["error_message"] = "Benchmark cancelled"
                    return out
                _ = f.read(CHUNK_SIZE)
                if progress_callback and i % 16 == 0:
                    pct = int(40 + (i / total_chunks) * 25)
                    progress_callback(pct, "Reading benchmark data...")
        read_duration = max(0.001, time.perf_counter() - t0)
        out["seq_read_mb_s"] = round(size_mb / read_duration, 1)

        # 3. Random 4K Read IOPS Test
        if progress_callback:
            progress_callback(70, "Testing random 4K read IOPS...")

        file_bytes = size_mb * 1024 * 1024
        max_4k_slots = (file_bytes - BLOCK_4K) // BLOCK_4K
        test_ops = 500  # 500 random operations

        t0 = time.perf_counter()
        with open(bench_file, "rb") as f:
            for _ in range(test_ops):
                slot = random.randint(0, max_4k_slots)
                f.seek(slot * BLOCK_4K)
                _ = f.read(BLOCK_4K)
        rand_read_time = max(0.001, time.perf_counter() - t0)
        out["random_4k_read_iops"] = int(test_ops / rand_read_time)

        # 4. Random 4K Write IOPS Test
        if progress_callback:
            progress_callback(85, "Testing random 4K write IOPS...")

        block_4k_data = os.urandom(BLOCK_4K)
        t0 = time.perf_counter()
        with open(bench_file, "r+b") as f:
            for _ in range(test_ops):
                slot = random.randint(0, max_4k_slots)
                f.seek(slot * BLOCK_4K)
                f.write(block_4k_data)
            f.flush()
            os.fsync(f.fileno())
        rand_write_time = max(0.001, time.perf_counter() - t0)
        out["random_4k_write_iops"] = int(test_ops / rand_write_time)

        if progress_callback:
            progress_callback(100, "Disk benchmark complete.")

    except Exception as e:
        logger.exception("Disk benchmark error: %s", e)
        out["error_message"] = str(e)
    finally:
        cleanup_manager.cleanup_file(bench_file)
        out["duration_s"] = round(time.perf_counter() - start_total, 2)

    return out
