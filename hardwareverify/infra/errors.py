"""Custom exception hierarchy for HardwareVerify."""


class HardwareVerifyError(Exception):
    """Base exception for all HardwareVerify errors."""
    pass


class UnsupportedPlatformError(HardwareVerifyError):
    """Raised when running on an unsupported platform."""
    def __init__(self, platform: str):
        self.platform = platform
        super().__init__(f"Unsupported platform: {platform}. Only Windows is currently supported.")


class HardwareReadError(HardwareVerifyError):
    """Raised when a hardware reading fails."""
    def __init__(self, source: str, detail: str):
        self.source = source
        self.detail = detail
        super().__init__(f"Failed to read from {source}: {detail}")


class WMIQueryError(HardwareReadError):
    """Raised when a WMI query fails."""
    def __init__(self, wmi_class: str, detail: str):
        super().__init__(f"WMI:{wmi_class}", detail)
        self.wmi_class = wmi_class


class SmartctlError(HardwareReadError):
    """Raised when smartctl fails or is not found."""
    def __init__(self, detail: str):
        super().__init__("smartctl", detail)


class TestCancelledError(HardwareVerifyError):
    """Raised when a test is cancelled by the user."""
    pass


class AdminRequiredError(HardwareVerifyError):
    """Raised when admin privileges are required but not available."""
    def __init__(self, operation: str):
        self.operation = operation
        super().__init__(
            f"Administrator privileges required for: {operation}. "
            f"Please restart the application as Administrator."
        )


class SensorUnavailableError(HardwareVerifyError):
    """Raised when a sensor is not available on this hardware."""
    def __init__(self, sensor: str, reason: str):
        self.sensor = sensor
        self.reason = reason
        super().__init__(f"Sensor '{sensor}' unavailable: {reason}")
