"""Core data models for hardware readings with provenance tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class Confidence(Enum):
    """Confidence level for a hardware reading.

    HIGH:   Two or more independent sources agree on the value.
    MEDIUM: Single authoritative source, no contradicting data.
    LOW:    Indirect measurement, estimation, or sources disagree.
    """
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Status(Enum):
    """Overall status for a module or check."""
    PASS = "Pass"
    WARNING = "Warning"
    FAIL = "Fail"
    NOT_TESTED = "Not Tested"


class BatteryHealth(Enum):
    """Battery health verdict based on wear percentage."""
    EXCELLENT = "Excellent"   # < 10% wear
    GOOD = "Good"             # 10–25% wear
    FAIR = "Fair"             # 25–40% wear
    REPLACE = "Replace"       # > 40% wear
    UNKNOWN = "Unknown"       # Cannot determine


@dataclass(frozen=True)
class DataSource:
    """Records where a hardware reading came from.

    Attributes:
        name: Identifier for the source (e.g. "WMI:Win32_Battery", "smartctl", "psutil").
        raw_value: The exact value returned by the source, before any processing.
        timestamp: When the reading was taken.
    """
    name: str
    raw_value: Any
    timestamp: datetime = field(default_factory=datetime.now)

    def __repr__(self) -> str:
        return f"DataSource({self.name!r}, raw={self.raw_value!r})"


@dataclass
class VerifiedValue(Generic[T]):
    """A hardware reading with full provenance and confidence tracking.

    Every value displayed in the UI is wrapped in a VerifiedValue so the user
    can see exactly where it came from and how trustworthy it is.

    Attributes:
        value: The resolved/displayed value (None if unavailable).
        sources: All data sources consulted for this value.
        confidence: How confident we are in this value.
        unavailable_reason: If set, the value could not be read; this explains why.
    """
    value: T | None
    sources: list[DataSource] = field(default_factory=list)
    confidence: Confidence = Confidence.MEDIUM
    unavailable_reason: str | None = None

    @property
    def is_available(self) -> bool:
        """True if the value was successfully read."""
        return self.unavailable_reason is None and self.value is not None

    @staticmethod
    def unavailable(reason: str, sources: list[DataSource] | None = None) -> VerifiedValue:
        """Create an unavailable value with an explanation.

        Args:
            reason: Human-readable reason why the value is unavailable.
            sources: Any sources that were attempted.
        """
        return VerifiedValue(
            value=None,
            sources=sources or [],
            confidence=Confidence.LOW,
            unavailable_reason=reason,
        )

    @staticmethod
    def from_single(value: T, source_name: str, raw_value: Any = None) -> VerifiedValue[T]:
        """Create a value from a single source (MEDIUM confidence).

        Args:
            value: The processed value.
            source_name: Name of the data source.
            raw_value: Raw value from the source (defaults to value).
        """
        return VerifiedValue(
            value=value,
            sources=[DataSource(name=source_name, raw_value=raw_value if raw_value is not None else value)],
            confidence=Confidence.MEDIUM,
        )

    @staticmethod
    def from_cross_validated(
        value: T,
        sources: list[DataSource],
        all_agree: bool,
    ) -> VerifiedValue[T]:
        """Create a value from multiple cross-validated sources.

        Args:
            value: The resolved value (typically from the most authoritative source).
            sources: All sources consulted.
            all_agree: True if all sources returned consistent values.
        """
        return VerifiedValue(
            value=value,
            sources=sources,
            confidence=Confidence.HIGH if all_agree else Confidence.LOW,
        )


@dataclass
class ModuleResult:
    """Result from a single hardware module's scan.

    Attributes:
        module_name: Identifier for the module (e.g. "system_identity", "battery").
        display_name: Human-friendly name (e.g. "System Identity", "Battery").
        status: Overall pass/warning/fail/not-tested status.
        health_score: 0–100 health score (100 = perfect).
        readings: Dict of reading names to their verified values.
        warnings: List of human-readable warning messages.
        errors: List of human-readable critical error messages.
        test_duration: How long the module scan took in seconds.
        timestamp: When the scan completed.
        icon: Optional emoji/icon for the module.
    """
    module_name: str
    display_name: str
    status: Status = Status.NOT_TESTED
    health_score: int = 100
    readings: dict[str, VerifiedValue] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    test_duration: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    icon: str = "🔍"
    is_applicable: bool = True

    def add_reading(self, name: str, value: VerifiedValue) -> None:
        """Add a reading to this module's results."""
        self.readings[name] = value

    def add_warning(self, message: str) -> None:
        """Add a warning message and update status."""
        self.warnings.append(message)
        if self.status == Status.PASS:
            self.status = Status.WARNING

    def add_error(self, message: str) -> None:
        """Add an error message and set status to FAIL."""
        self.errors.append(message)
        self.status = Status.FAIL

    def deduct_score(self, points: int, reason: str | None = None) -> None:
        """Deduct points from the health score (floor at 0).

        Args:
            points: Points to deduct.
            reason: Optional reason (added as warning if provided).
        """
        self.health_score = max(0, self.health_score - points)
        if reason:
            self.add_warning(reason)

    def finalize(self, duration: float) -> None:
        """Finalize the result after all readings are collected.

        Sets the final status based on score, warnings, and errors.
        Preserves NOT_TESTED if is_applicable is False.
        """
        self.test_duration = duration
        self.timestamp = datetime.now()

        if not self.is_applicable:
            self.status = Status.NOT_TESTED
            return

        if self.errors or self.health_score < 50:
            self.status = Status.FAIL
        elif self.warnings or self.health_score < 80:
            self.status = Status.WARNING
        else:
            self.status = Status.PASS


# --- Tooltip descriptions for readings ---

READING_TOOLTIPS: dict[str, str] = {
    # System Identity
    "manufacturer": "The company that made this computer.",
    "model": "The specific model name/number of this computer.",
    "serial_number": "A unique identifier for this specific machine. Fake or blank serials are a red flag.",
    "bios_version": "The firmware version running on the motherboard.",
    "bios_date": "When the BIOS firmware was released. Should align with the computer's age.",
    "motherboard": "The main circuit board (mainboard) model.",
    "os_build": "The Windows version and build number.",
    "windows_activation": "Whether Windows is genuinely activated on this machine.",

    # Battery
    "design_capacity": "The battery capacity when new, as designed by the manufacturer (in mWh).",
    "full_charge_capacity": "The battery's current maximum charge capacity (in mWh). Decreases with age and use.",
    "wear_percentage": "How much capacity the battery has lost. Lower is better.",
    "cycle_count": "How many full charge-discharge cycles the battery has gone through.",
    "chemistry": "The battery chemistry type (e.g. Li-ion, Li-polymer).",
    "charge_rate": "How fast the battery is currently charging (in mW).",
    "discharge_rate": "How fast the battery is currently draining (in mW).",
    "battery_health": "Overall health verdict based on wear percentage.",
    "discharge_stability": "Whether the battery drains at a steady rate, or has dangerous sudden drops.",

    # Storage
    "disk_model": "The manufacturer and model of this storage drive.",
    "disk_serial": "The drive's unique serial number.",
    "disk_firmware": "The drive's firmware version.",
    "disk_interface": "How the drive connects (SATA, NVMe, USB).",
    "disk_capacity": "Total storage capacity of the drive.",
    "smart_health": "Self-Monitoring, Analysis, and Reporting Technology health status.",
    "power_on_hours": "Total hours the drive has been powered on.",
    "power_cycles": "Number of times the drive has been turned on and off.",
    "reallocated_sectors": "Bad sectors the drive has replaced with spares. High count = dying drive.",
    "pending_sectors": "Sectors waiting to be reallocated. Any pending sectors are concerning.",
    "media_errors": "Errors in the storage media. Should be zero for a healthy drive.",
    "percentage_used": "How much of the drive's total endurance has been consumed (SSDs only).",
    "total_data_written": "Total amount of data written to the drive over its lifetime.",
    "disk_temperature": "Current drive temperature in °C.",

    # RAM
    "total_ram": "Total installed system memory.",
    "ram_slots": "Physical memory slots and what's installed in each.",
    "dual_channel": "Whether RAM is running in dual-channel mode (doubles memory bandwidth).",
    "ram_speed": "The speed the RAM is actually running at vs. its rated speed.",

    # CPU
    "cpu_model": "The processor model name.",
    "cpu_cores": "Number of physical CPU cores.",
    "cpu_threads": "Number of logical threads (includes hyperthreading).",
    "cpu_base_clock": "The guaranteed base clock speed.",
    "cpu_boost_clock": "The maximum boost clock speed under optimal conditions.",
    "cpu_cache": "CPU cache sizes (L1/L2/L3).",
    "cpu_virtualization": "Whether hardware virtualization is supported and enabled.",
    "cpu_spoof_check": "Whether the CPU name matches its actual specifications.",

    # GPU
    "gpu_model": "The graphics card model name.",
    "gpu_vram": "Video memory (VRAM) on the graphics card.",
    "gpu_driver": "The installed graphics driver version.",
    "gpu_type": "Whether this is an integrated (built into CPU) or dedicated graphics card.",

    # Display
    "resolution": "Screen resolution in pixels (width × height).",
    "refresh_rate": "How many times per second the display updates (Hz). Higher is smoother.",
    "panel_size": "Physical diagonal size of the display in inches.",

    # Security
    "secure_boot": "Whether Secure Boot is enabled (protects against boot-level malware).",
    "tpm_present": "Whether a Trusted Platform Module is present (needed for Windows 11, BitLocker).",
    "mdm_enrolled": "Whether the device is enrolled in Mobile Device Management (enterprise control).",
    "domain_joined": "Whether the device is joined to a corporate domain or Azure AD.",
}
