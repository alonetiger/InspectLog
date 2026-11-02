"""Core hardware abstraction layer and data models."""

from hardwareverify.core.models import (
    Confidence,
    Status,
    BatteryHealth,
    DataSource,
    VerifiedValue,
    ModuleResult,
    READING_TOOLTIPS,
)
from hardwareverify.core.hal_interface import HardwareReaderInterface
from hardwareverify.core.platform_factory import create_hal
from hardwareverify.core.cross_validator import cross_validate, cross_validate_numeric

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
