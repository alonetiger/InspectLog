"""Safe WMI query wrappers with COM initialization and error handling."""

from __future__ import annotations

from typing import Any
import sys

from inspectlog.infra.logging import get_logger

logger = get_logger("wmi_helpers")

# Attempt pythoncom import for thread-safe COM initialization
try:
    import pythoncom
    HAS_PYTHONCOM = True
except ImportError:
    HAS_PYTHONCOM = False

try:
    import wmi
    HAS_WMI = True
except ImportError:
    HAS_WMI = False


def ensure_com_initialized() -> None:
    """Ensure COM is initialized for the current thread."""
    if HAS_PYTHONCOM:
        try:
            pythoncom.CoInitialize()
        except Exception:
            pass


def uninitialize_com() -> None:
    """Uninitialize COM for the current thread."""
    if HAS_PYTHONCOM:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def safe_wmi_query(
    wmi_class: str,
    namespace: str = "root/cimv2",
    fields: list[str] | None = None,
    where: str | None = None,
) -> list[dict[str, Any]]:
    """Query a WMI class safely without throwing unhandled exceptions.

    Args:
        wmi_class: The WMI class name (e.g. 'Win32_ComputerSystem').
        namespace: The WMI namespace (default: 'root/cimv2', or 'root/wmi', etc.).
        fields: Optional list of property names to retrieve. If None, retrieves all available.
        where: Optional WHERE clause (e.g. "ApplicationID='...'").

    Returns:
        List of dictionaries with property names and their values.
        Returns empty list on any failure or if class not found.
    """
    if sys.platform != "win32" or not HAS_WMI:
        logger.debug("WMI query skipped: not on Windows or wmi package not installed")
        return []

    ensure_com_initialized()

    try:
        c = wmi.WMI(namespace=namespace)
        query = f"SELECT * FROM {wmi_class}"
        if where:
            query += f" WHERE {where}"

        raw_results = c.query(query)
        output: list[dict[str, Any]] = []

        for item in raw_results:
            row: dict[str, Any] = {}
            if fields:
                for f in fields:
                    try:
                        row[f] = getattr(item, f, None)
                    except Exception:
                        row[f] = None
            else:
                # Extract all properties from WMI object
                try:
                    for prop in item.properties:
                        try:
                            row[prop] = getattr(item, prop, None)
                        except Exception:
                            row[prop] = None
                except Exception:
                    pass
            output.append(row)

        return output
    except Exception as e:
        logger.debug(
            "WMI query failed for class '%s' in namespace '%s': %s",
            wmi_class, namespace, e
        )
        return []


def safe_wmi_value(
    wmi_class: str,
    field: str,
    namespace: str = "root/cimv2",
    where: str | None = None,
    index: int = 0,
) -> Any | None:
    """Retrieve a single property value from a WMI query.

    Returns None if the query fails or index is out of bounds.
    """
    rows = safe_wmi_query(wmi_class, namespace=namespace, fields=[field], where=where)
    if rows and len(rows) > index:
        return rows[index].get(field)
    return None
