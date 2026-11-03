"""Windows Hardware Reader implementation implementing HardwareReaderInterface."""

from __future__ import annotations

from inspectlog.core.hal_interface import HardwareReaderInterface
from inspectlog.core.models import ModuleResult, Status
from inspectlog.core.windows.battery_reader import BatteryReader
from inspectlog.core.windows.cpu_reader import CPUReader
from inspectlog.core.windows.display_reader import DisplayReader
from inspectlog.core.windows.gpu_reader import GPUReader
from inspectlog.core.windows.input_reader import InputReader
from inspectlog.core.windows.ram_reader import RAMReader
from inspectlog.core.windows.security_reader import SecurityReader
from inspectlog.core.windows.storage_reader import StorageReader
from inspectlog.core.windows.system_reader import SystemReader
from inspectlog.core.windows.thermal_reader import ThermalReader
from inspectlog.infra.logging import get_logger

logger = get_logger("hardware_reader")


class WindowsHardwareReader(HardwareReaderInterface):
    """Orchestrates hardware reads across Windows subsystems."""

    def __init__(self) -> None:
        self._system_reader = SystemReader()
        self._battery_reader = BatteryReader()
        self._storage_reader = StorageReader()
        self._ram_reader = RAMReader()
        self._cpu_reader = CPUReader()
        self._gpu_reader = GPUReader()
        self._display_reader = DisplayReader()
        self._thermal_reader = ThermalReader()
        self._security_reader = SecurityReader()
        self._input_reader = InputReader()

    def read_system_identity(self) -> ModuleResult:
        """Read system identity and motherboard telemetry."""
        return self._system_reader.read_system_identity()

    def read_battery(self) -> ModuleResult:
        """Read battery parameters, health, and wear."""
        return self._battery_reader.read_battery()

    def read_storage(self) -> list[ModuleResult]:
        """Read physical storage drives and SMART health telemetry."""
        return self._storage_reader.read_storage()

    def read_ram(self) -> ModuleResult:
        """Read RAM modules, speeds, and dual-channel topology."""
        return self._ram_reader.read_ram()

    def read_cpu(self) -> ModuleResult:
        """Read CPU model, core/thread counts, cache, and spoof status."""
        return self._cpu_reader.read_cpu()

    def read_gpu(self) -> list[ModuleResult]:
        """Read GPU adapters, verified VRAM, and driver versions."""
        return self._gpu_reader.read_gpu()

    def read_display(self) -> list[ModuleResult]:
        """Read connected display panels, resolution, refresh rate, and EDID data."""
        return self._display_reader.read_display()

    def read_thermals(self) -> ModuleResult:
        """Read ACPI thermal zones and hardware sensor temperatures."""
        return self._thermal_reader.read_thermals()

    def read_security(self) -> ModuleResult:
        """Read Secure Boot, TPM, MDM enrollment, and locks."""
        return self._security_reader.read_security()

    def read_input(self) -> ModuleResult:
        """Read input devices, wireless adapters, audio codecs, and USB controllers."""
        return self._input_reader.read_input()
