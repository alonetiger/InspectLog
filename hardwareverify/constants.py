"""Application-wide constants."""

APP_NAME = "InspectLog"
APP_VERSION = "1.0.0"
APP_DISPLAY_NAME = "Inspect Log"

# Paths
import os
import sys
import tempfile

if getattr(sys, "frozen", False):
    # PyInstaller temporary extraction directory
    BASE_DIR = sys._MEIPASS
    PKG_DIR = os.path.join(BASE_DIR, "hardwareverify")
    ROOT_DIR = BASE_DIR
else:
    PKG_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.dirname(PKG_DIR)

APP_TEMP_DIR = os.path.join(tempfile.gettempdir(), "InspectLog")
ASSETS_DIR = os.path.join(PKG_DIR, "ui", "assets")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
ICON_PATH = os.path.join(ASSETS_DIR, "app_icon.ico")
SMARTCTL_PATH = os.path.join(ROOT_DIR, "tools", "smartmontools", "smartctl.exe")

# Battery health thresholds (wear %)
BATTERY_EXCELLENT_THRESHOLD = 10.0
BATTERY_GOOD_THRESHOLD = 25.0
BATTERY_FAIR_THRESHOLD = 40.0
# > 40% = Replace

# Stress test defaults
CPU_STRESS_DURATION_QUICK_S = 30
CPU_STRESS_DURATION_FULL_S = 180
THERMAL_THROTTLE_DROP_PCT = 10.0
THERMAL_EMERGENCY_STOP_C = 95.0

# Scoring weights (sum to 100)
SCORING_WEIGHTS = {
    "system_identity": 5,
    "battery": 15,
    "storage": 20,
    "ram": 10,
    "cpu": 15,
    "gpu": 10,
    "display": 10,
    "input_io": 5,
    "thermals": 5,
    "security": 5,
}

# Known placeholder/fake serial numbers
FAKE_SERIALS = {
    "to be filled by o.e.m.",
    "default string",
    "system serial number",
    "not applicable",
    "none",
    "n/a",
    "chassis serial number",
    "0",
    "bsn12345678901234567",
    "",
}
