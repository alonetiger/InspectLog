"""Core hardware abstraction layer and data models."""

from inspectlog.core.models import (
    Confidence,
    Status,
    BatteryHealth,
    DataSource,
    VerifiedValue,
    ModuleResult,
    READING_TOOLTIPS,
)
from inspectlog.core.hal_interface import HardwareReaderInterface
from inspectlog.core.platform_factory import create_hal
from inspectlog.core.cross_validator import cross_validate, cross_validate_numeric

__all__ = [
    "Confidence",
    "Status",
    "BatteryHealth",
    "DataSource",
    "VerifiedValue",
    "ModuleResult",
    "READING_TOOLTIPS",
    "HardwareReaderInterface",
    "create_hal",
    "cross_validate",
    "cross_validate_numeric",
]
