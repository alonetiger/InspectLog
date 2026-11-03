"""Safe counterfeit storage and fake-capacity verification test."""

from __future__ import annotations

import hashlib
import os
import tempfile
import time
from typing import Callable

from hardwareverify.infra.cleanup import cleanup_manager
from hardwareverify.infra.logging import get_logger

logger = get_logger("fake_capacity")

BLOCK_SIZE = 64 * 1024  # 64 KB block


def generate_test_block(seed: int, length: int = BLOCK_SIZE) -> bytes:
    """Generate deterministic byte pattern for a given block seed."""
    header = f"HWV_BLOCK_{seed:08d}".encode("utf-8")
    payload_hash = hashlib.sha256(f"seed_{seed}".encode("utf-8")).digest()
    # Repeat hash pattern to fill length
    pattern = (payload_hash * (length // len(payload_hash) + 1))[:length]
    return header + pattern[len(header):]


def verify_test_block(data: bytes, seed: int) -> bool:
    """Verify that the read data matches the expected seed pattern."""
    expected = generate_test_block(seed, len(data))
    return data == expected


def run_fake_capacity_check(
    target_dir: str | None = None,
    test_size_mb: int = 256,
    progress_callback: Callable[[int, str], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Execute a non-destructive block write-and-verify test to catch counterfeit flash storage.

    Args:
        target_dir: Directory on the drive to test (defaults to system temp).
        test_size_mb: Size of temporary verification container in MB.
        progress_callback: Optional callback receiving (percentage, status_msg).
        cancel_check: Optional callable returning True if user cancelled test.

    Returns:
        Dict with keys:
            is_genuine: bool (True if all checkpoints matched, False if counterfeit)
            blocks_tested: int
            errors_detected: int
            mismatch_offsets: list[int]
            test_file_path: str
            duration_s: float
            error_message: str | None
    """
    start_time = time.perf_counter()
    target_dir = target_dir or tempfile.gettempdir()
    test_file = os.path.join(target_dir, f".hwv_fake_check_{int(time.time()*1000)}.tmp")
    cleanup_manager.register_file(test_file)

    result: dict[str, Any] = {
        "is_genuine": True,
        "blocks_tested": 0,
        "errors_detected": 0,
        "mismatch_offsets": [],
        "test_file_path": test_file,
        "duration_s": 0.0,
        "error_message": None,
    }

    total_bytes = test_size_mb * 1024 * 1024
    num_blocks = 8  # 8 evenly distributed checkpoints
    step = (total_bytes - BLOCK_SIZE) // (num_blocks - 1)
    offsets = [i * step for i in range(num_blocks)]

    try:
        if progress_callback:
            progress_callback(5, "Creating safe verification file...")

        # Step 1: Write test blocks at spaced offsets
        with open(test_file, "wb") as f:
            fd = f.fileno()
            for idx, offset in enumerate(offsets):
                if cancel_check and cancel_check():
                    result["error_message"] = "Test cancelled by user"
                    return result

                f.seek(offset)
                block_data = generate_test_block(seed=idx, length=BLOCK_SIZE)
                f.write(block_data)

                if progress_callback:
                    pct = int(10 + (idx / len(offsets)) * 40)
                    progress_callback(pct, f"Writing block {idx+1}/{len(offsets)} at offset {offset//(1024*1024)}MB...")

            f.flush()
            os.fsync(fd)  # Flush OS write cache directly to hardware

        if progress_callback:
            progress_callback(55, "Flushed cache. Verifying data integrity...")

        # Step 2: Read back and verify all blocks
        with open(test_file, "rb") as f:
            for idx, offset in enumerate(offsets):
                if cancel_check and cancel_check():
                    result["error_message"] = "Test cancelled by user"
                    return result

                f.seek(offset)
                read_data = f.read(BLOCK_SIZE)
                result["blocks_tested"] += 1

                if not verify_test_block(read_data, seed=idx):
                    result["errors_detected"] += 1
                    result["mismatch_offsets"].append(offset)
                    result["is_genuine"] = False
                    logger.warning("Integrity mismatch at offset %d (block seed %d)", offset, idx)

                if progress_callback:
                    pct = int(60 + (idx / len(offsets)) * 38)
                    progress_callback(pct, f"Verifying block {idx+1}/{len(offsets)}...")

        if result["errors_detected"] > 0:
            result["is_genuine"] = False
            result["error_message"] = (
                f"Data integrity failed at {result['errors_detected']} offsets! "
                f"High probability of counterfeit/fake-capacity storage or failing NAND flash."
            )

        if progress_callback:
            progress_callback(100, "Integrity verification complete.")

    except Exception as e:
        logger.exception("Fake capacity test encountered error: %s", e)
        result["is_genuine"] = False
        result["error_message"] = str(e)
    finally:
        cleanup_manager.cleanup_file(test_file)
        result["duration_s"] = round(time.perf_counter() - start_time, 2)

    return result
