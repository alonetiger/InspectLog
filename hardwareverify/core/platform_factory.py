"""Platform factory — returns the correct HAL for the current OS."""

import sys

from hardwareverify.core.hal_interface import HardwareReaderInterface
from hardwareverify.infra.errors import UnsupportedPlatformError


def create_hal() -> HardwareReaderInterface:
    """Create and return the hardware reader for the current platform.

    Returns:
        A platform-specific HardwareReaderInterface implementation.

    Raises:
        UnsupportedPlatformError: If the current OS is not supported.
    """
    if sys.platform == "win32":
        # Import here to avoid loading Windows-specific modules on other platforms
        from hardwareverify.core.windows.hardware_reader import WindowsHardwareReader
        return WindowsHardwareReader()
    # Future: elif sys.platform == "linux": ...
    # Future: elif sys.platform == "darwin": ...
    raise UnsupportedPlatformError(sys.platform)
