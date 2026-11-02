# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification file for Inspect Log (single portable executable)."""

import os
import sys

block_cipher = None

# Spec path is tools/build, project root is two levels up
SPEC_DIR = os.path.abspath(SPECPATH)
PROJECT_ROOT = os.path.abspath(os.path.join(SPEC_DIR, "..", ".."))

entrypoint = os.path.join(PROJECT_ROOT, "hardwareverify", "__main__.py")
icon_path = os.path.join(PROJECT_ROOT, "hardwareverify", "ui", "assets", "app_icon.ico")
manifest_path = os.path.join(SPEC_DIR, "manifest.xml")

datas = [
    (os.path.join(PROJECT_ROOT, "hardwareverify", "ui", "assets", "logo.png"), "hardwareverify/ui/assets"),
    (os.path.join(PROJECT_ROOT, "hardwareverify", "ui", "assets", "app_icon.ico"), "hardwareverify/ui/assets"),
    (os.path.join(PROJECT_ROOT, "tools", "smartmontools", "smartctl.exe"), "tools/smartmontools"),
]

hiddenimports = [
    "wmi",
    "win32api",
    "win32con",
    "win32gui",
    "win32process",
    "cpuinfo",
    "pynvml",
    "psutil",
    "numpy",
    "reportlab",
    "reportlab.lib",
    "reportlab.lib.colors",
    "reportlab.lib.pagesizes",
    "reportlab.lib.styles",
    "reportlab.lib.units",
    "reportlab.platypus",
    "reportlab.platypus.flowables",
    "reportlab.platypus.paragraph",
    "reportlab.platypus.tables",
    "reportlab.pdfgen",
    "reportlab.pdfgen.canvas",
    "reportlab.graphics",
    "PIL",
    "PIL.Image",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
]

a = Analysis(
    [entrypoint],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy", "notebook", "IPython"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="InspectLog",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
    uac_admin=True,
    uac_uiaccess=False,
)
