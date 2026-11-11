# PyInstaller spec for the single-file InspectLog.exe.
# Build from the repo root:
#   py -m PyInstaller tools/build/inspectlog.spec --clean --distpath dist --workpath build
# -*- mode: python ; coding: utf-8 -*-

import os

ROOT = os.path.abspath(os.path.join(SPECPATH, "..", ".."))

a = Analysis(
    [os.path.join(ROOT, "hardwareverify", "__main__.py")],
    pathex=[ROOT],
    binaries=[
        (os.path.join(ROOT, "tools", "smartmontools", "smartctl.exe"), os.path.join("tools", "smartmontools")),
    ],
    datas=[
        (os.path.join(ROOT, "hardwareverify", "ui", "assets"), os.path.join("hardwareverify", "ui", "assets")),
    ],
    hiddenimports=[
        "win32timezone",
        "pythoncom",
        "pywintypes",
        "wmi",
    ],
    excludes=["tkinter", "pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="InspectLog",
    icon=os.path.join(ROOT, "hardwareverify", "ui", "assets", "app_icon.ico"),
    manifest=os.path.join(SPECPATH, "inspectlog.manifest"),
    uac_admin=True,
    console=False,
    upx=False,
    debug=False,
    strip=False,
    runtime_tmpdir=None,
)
