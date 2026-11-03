"""Hardware Abstraction Layer (HAL) interface.

Defines the abstract interface that all platform-specific hardware readers
must implement. This ensures a clean separation between the core logic
and platform-specific code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from inspectlog.core.models import ModuleResult


class HardwareReaderInterface(ABC):
    """Abstract interface for platform-specific hardware readers.

    Each platform (Windows, Linux, macOS) implements this interface
    with its own system calls, WMI queries, sysfs reads, etc.
    """

    @abstractmethod
    def read_system_identity(self) -> ModuleResult:
        """Read system identity information.

        Includes: manufacturer, model, serial number, BIOS version/date,
        motherboard, OS build, Windows activation status.
        """
        ...

    @abstractmethod
    def read_battery(self) -> ModuleResult:
        """Read battery information.

        Includes: design capacity, full charge capacity, wear percentage,
        cycle count, chemistry, charge/discharge rate, health verdict.

        Returns a result with status NOT_TESTED and a note if no battery
        is present (e.g. desktop PC).
        """
        ...

    @abstractmethod
    def read_storage(self) -> list[ModuleResult]:
        """Read storage device information for all drives.

        Returns one ModuleResult per detected storage device.
        Includes: model, serial, firmware, interface, capacity,
        SMART health, power-on hours, etc.
        """
        ...

    @abstractmethod
    def read_ram(self) -> ModuleResult:
        """Read RAM information.

        Includes: total capacity, per-slot details, dual-channel status,
        actual vs rated speed.
        """
        ...

    @abstractmethod
    def read_cpu(self) -> ModuleResult:
        """Read CPU information.

        Includes: model, cores/threads, clocks, cache, virtualization,
        spoof detection.
        """
        ...

    @abstractmethod
    def read_gpu(self) -> list[ModuleResult]:
        """Read GPU information for all graphics adapters.

        Returns one ModuleResult per detected GPU.
        Includes: model, VRAM, driver, integrated vs dedicated.
        """
        ...

    @abstractmethod
    def read_display(self) -> list[ModuleResult]:
        """Read display/monitor information.

        Returns one ModuleResult per detected display.
        Includes: resolution, refresh rate, panel size.
        """
        ...

    @abstractmethod
    def read_thermals(self) -> ModuleResult:
        """Read thermal and fan sensor data.

        Includes: CPU/GPU temperatures, fan RPMs, voltages.
        """
        ...

    @abstractmethod
    def read_security(self) -> ModuleResult:
        """Read security and lock status.

        Includes: Secure Boot, TPM, BIOS password, MDM enrollment,
        domain join status.
        """
        ...

    @abstractmethod
    def read_input(self) -> ModuleResult:
        """Read input and peripheral devices (Wi-Fi, Bluetooth, Audio, Webcam, USB)."""
        ...
