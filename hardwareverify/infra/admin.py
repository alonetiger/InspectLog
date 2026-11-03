"""Administrator privilege detection and UAC elevation."""

import ctypes
import sys

from hardwareverify.infra.logging import get_logger

logger = get_logger("admin")


def is_admin() -> bool:
    """Check if the current process has administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except (AttributeError, OSError):
        # Not on Windows or API unavailable
        return False


def check_admin_status() -> dict[str, bool]:
    """Return a dict with admin status info for the UI.

    Returns:
        Dict with keys:
        - is_admin: True if running elevated
        - smart_available: True if SMART queries will work
        - wmi_full_access: True if all WMI namespaces accessible
    """
    admin = is_admin()
    return {
        "is_admin": admin,
        "smart_available": admin,  # smartctl needs admin
        "wmi_full_access": admin,  # Some WMI classes need admin
    }


def request_elevation() -> bool:
    """Attempt to re-launch the current process with admin rights.

    Returns True if elevation was requested (current process should exit).
    Returns False if elevation was declined or failed.
    """
    if is_admin():
        return False

    try:
        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            " ".join(sys.argv),
            None,
            1  # SW_SHOWNORMAL
        )
        # ShellExecuteW returns > 32 on success
        return result > 32
    except (AttributeError, OSError) as e:
        logger.error("Failed to request elevation: %s", e)
        return False
