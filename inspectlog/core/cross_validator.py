"""Cross-validation engine for comparing readings from multiple sources."""

from __future__ import annotations

from typing import Any, Callable

from inspectlog.core.models import Confidence, DataSource, VerifiedValue
from inspectlog.infra.logging import get_logger

logger = get_logger("cross_validator")


# Type alias for a comparison function
CompareFunc = Callable[[Any, Any], bool]


def _default_compare(a: Any, b: Any) -> bool:
    """Default comparison: exact equality after stripping and lowering strings."""
    if isinstance(a, str) and isinstance(b, str):
        return a.strip().lower() == b.strip().lower()
    return a == b


def _numeric_compare(tolerance_pct: float = 5.0) -> CompareFunc:
    """Create a numeric comparison function with a percentage tolerance.

    Args:
        tolerance_pct: Acceptable difference as a percentage of the first value.
    """
    def compare(a: Any, b: Any) -> bool:
        try:
            fa, fb = float(a), float(b)
            if fa == 0:
                return fb == 0
            return abs(fa - fb) / abs(fa) * 100 <= tolerance_pct
        except (TypeError, ValueError, ZeroDivisionError):
            return a == b
    return compare


def cross_validate(
    readings: list[tuple[str, Any]],
    compare: CompareFunc | None = None,
    primary_source_index: int = 0,
) -> VerifiedValue:
    """Cross-validate a value from multiple sources.

    Args:
        readings: List of (source_name, value) tuples. Each source is checked.
                  A value of None means the source failed to return data.
        compare: Custom comparison function. Defaults to string-normalized equality.
        primary_source_index: Index of the most authoritative source (used as the
                            resolved value when sources agree).

    Returns:
        A VerifiedValue with appropriate confidence level:
        - HIGH if 2+ sources agree
        - MEDIUM if only 1 source returned data
        - LOW if sources disagree
    """
    if compare is None:
        compare = _default_compare

    # Filter out failed sources (None values)
    available: list[tuple[str, Any]] = [
        (name, val) for name, val in readings if val is not None
    ]
    all_sources = [
        DataSource(name=name, raw_value=val) for name, val in readings
    ]

    if not available:
        return VerifiedValue.unavailable(
            reason="No data source returned a value",
            sources=all_sources,
        )

    if len(available) == 1:
        name, val = available[0]
        logger.debug("Single source for value: %s = %r", name, val)
        return VerifiedValue(
            value=val,
            sources=all_sources,
            confidence=Confidence.MEDIUM,
        )

    # Multiple sources available — check agreement
    primary_name, primary_val = available[min(primary_source_index, len(available) - 1)]
    agreements = 0
    disagreements = []

    for name, val in available:
        if name == primary_name:
            continue
        if compare(primary_val, val):
            agreements += 1
        else:
            disagreements.append((name, val))

    if not disagreements:
        # All sources agree
        logger.debug(
            "Cross-validation: %d sources agree on %r",
            len(available), primary_val
        )
        return VerifiedValue.from_cross_validated(
            value=primary_val,
            sources=all_sources,
            all_agree=True,
        )
    else:
        # Sources disagree
        logger.warning(
            "Cross-validation DISAGREEMENT for %s=%r: %s",
            primary_name, primary_val,
            [(n, v) for n, v in disagreements]
        )
        return VerifiedValue(
            value=primary_val,
            sources=all_sources,
            confidence=Confidence.LOW,
        )


def cross_validate_numeric(
    readings: list[tuple[str, Any]],
    tolerance_pct: float = 5.0,
    primary_source_index: int = 0,
) -> VerifiedValue:
    """Cross-validate numeric values with a percentage tolerance.

    Args:
        readings: List of (source_name, numeric_value) tuples.
        tolerance_pct: Acceptable difference as a percentage.
        primary_source_index: Index of the most authoritative source.
    """
    return cross_validate(
        readings=readings,
        compare=_numeric_compare(tolerance_pct),
        primary_source_index=primary_source_index,
    )
