"""Reference hardware specifications for detecting spoofed CPU model names."""

from __future__ import annotations

import re
from typing import Any

# Maps structured regex pattern to (min_physical_cores, min_threads, min_l3_mb, display_name)
CPU_MODEL_RULES: list[tuple[re.Pattern, int, int, float, str]] = [
    # Intel Core i9
    (re.compile(r"i9-(?:14900|13900|12900)[kK]", re.IGNORECASE), 16, 24, 30.0, "Core i9 (12th-14th Gen)"),
    (re.compile(r"i9-(?:14900|13900|12900)[hH]", re.IGNORECASE), 14, 20, 24.0, "Core i9 Mobile (12th-14th Gen)"),
    (re.compile(r"i9-(?:11900|10900|9900)[kK]?", re.IGNORECASE), 8, 16, 16.0, "Core i9 (9th-11th Gen)"),

    # Intel Core i7
    (re.compile(r"i7-14700[kK]?", re.IGNORECASE), 20, 28, 33.0, "Core i7-14700"),
    (re.compile(r"i7-(?:13700|12700)[kK]?", re.IGNORECASE), 12, 20, 24.0, "Core i7 (12th-13th Gen)"),
    (re.compile(r"i7-(?:13700|12700)[hH]", re.IGNORECASE), 14, 20, 24.0, "Core i7 Mobile (12th-13th Gen)"),
    (re.compile(r"i7-(?:11700|10700)[kK]?", re.IGNORECASE), 8, 16, 16.0, "Core i7 (10th-11th Gen)"),
    (re.compile(r"i7-(?:9700)[kK]?", re.IGNORECASE), 8, 8, 12.0, "Core i7-9700"),
    (re.compile(r"i7-(?:8700)[kK]?", re.IGNORECASE), 6, 12, 12.0, "Core i7-8700"),
    (re.compile(r"i7-(?:7700|6700|4790|4770)[kK]?", re.IGNORECASE), 4, 8, 8.0, "Core i7 (4th-7th Gen Quad-Core)"),

    # Intel Core i5
    (re.compile(r"i5-(?:14600|13600)[kK]?", re.IGNORECASE), 14, 20, 24.0, "Core i5-13600/14600"),
    (re.compile(r"i5-(?:13500|13400|12600)[kK]?", re.IGNORECASE), 10, 16, 20.0, "Core i5 (10-Core Hybrid)"),
    (re.compile(r"i5-(?:12400|11400|10400|9400|8400)", re.IGNORECASE), 6, 6, 9.0, "Core i5 (6-Core)"),
    (re.compile(r"i5-(?:7400|6400|4460)", re.IGNORECASE), 4, 4, 6.0, "Core i5 (4th-7th Gen Quad-Core)"),

    # Intel Core i3
    (re.compile(r"i3-(?:14100|13100|12100)", re.IGNORECASE), 4, 8, 12.0, "Core i3 (12th-14th Gen Quad-Core)"),
    (re.compile(r"i3-(?:10100|9100|8100)", re.IGNORECASE), 4, 4, 6.0, "Core i3 (8th-10th Gen Quad-Core)"),
    (re.compile(r"i3-(?:7100|6006|6100|5005|4005)[uU]?", re.IGNORECASE), 2, 4, 3.0, "Core i3 Dual-Core"),

    # AMD Ryzen 9
    (re.compile(r"ryzen\s+9\s+(?:7950|5950|3950)", re.IGNORECASE), 16, 32, 64.0, "Ryzen 9 (16-Core)"),
    (re.compile(r"ryzen\s+9\s+(?:7900|5900|3900)", re.IGNORECASE), 12, 24, 64.0, "Ryzen 9 (12-Core)"),

    # AMD Ryzen 7
    (re.compile(r"ryzen\s+7\s+(?:7800|7700|5800|5700|3700|2700|1700)", re.IGNORECASE), 8, 16, 16.0, "Ryzen 7 (8-Core)"),

    # AMD Ryzen 5
    (re.compile(r"ryzen\s+5\s+(?:7600|7500|5600|5500|3600|2600|1600)", re.IGNORECASE), 6, 12, 16.0, "Ryzen 5 (6-Core)"),
    (re.compile(r"ryzen\s+5\s+(?:3400|2400)", re.IGNORECASE), 4, 8, 4.0, "Ryzen 5 APU (4-Core)"),
]


def verify_cpu_authenticity(
    model_name: str,
    physical_cores: int,
    logical_threads: int,
    l3_cache_mb: float | None = None,
) -> tuple[bool, str]:
    """Verify that actual hardware physical cores and threads match the claimed model name.

    Returns:
        (is_authentic: bool, reason: str)
    """
    for pattern, min_cores, min_threads, min_l3, label in CPU_MODEL_RULES:
        if pattern.search(model_name):
            if physical_cores < min_cores:
                return False, (
                    f"SPOOFED CPU DETECTED: Claimed model '{model_name}' ({label}) requires at least "
                    f"{min_cores} physical cores, but hardware has only {physical_cores} cores!"
                )
            if logical_threads < min_threads:
                return False, (
                    f"SPOOFED CPU DETECTED: Claimed model '{model_name}' ({label}) requires at least "
                    f"{min_threads} threads, but hardware has only {logical_threads} threads!"
                )
            if l3_cache_mb is not None and l3_cache_mb > 0 and l3_cache_mb < (min_l3 * 0.4):
                return False, (
                    f"SPOOFED CPU DETECTED: Claimed model '{model_name}' expects ~{min_l3}MB L3 cache, "
                    f"but hardware reports only {l3_cache_mb}MB."
                )
            return True, f"Hardware cores ({physical_cores}) and threads ({logical_threads}) match specifications for {label}."

    # General heuristic checks
    norm = model_name.lower()
    if ("i9-" in norm or "core i9" in norm) and physical_cores < 8:
        return False, f"Suspicious CPU: Model claims to be an Intel Core i9, but only has {physical_cores} physical cores."
    if ("ryzen 9" in norm or "ryzen9" in norm) and physical_cores < 12:
        return False, f"Suspicious CPU: Model claims to be AMD Ryzen 9, but only has {physical_cores} physical cores."

    return True, f"CPU specification verification passed ({physical_cores} cores / {logical_threads} threads)."
