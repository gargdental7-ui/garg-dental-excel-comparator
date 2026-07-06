# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for the Garg Dental Excel Comparator.

Build with:  pyinstaller --noconfirm GargDentalExcelComparator.spec
Produces a windowed, onedir app in dist/GargDentalExcelComparator/.
The icon is optional - drop assets/app_icon.ico (Windows) or
assets/app_icon.icns (macOS) in place and rebuild to use it.
"""
import os
import sys

block_cipher = None

if sys.platform == "win32":
    _icon_candidate = os.path.join("assets", "app_icon.ico")
elif sys.platform == "darwin":
    _icon_candidate = os.path.join("assets", "app_icon.icns")
else:
    _icon_candidate = None

icon_path = _icon_candidate if _icon_candidate and os.path.exists(_icon_candidate) else None

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GargDentalExcelComparator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="GargDentalExcelComparator",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="GargDentalExcelComparator.app",
        icon=icon_path,
        bundle_identifier="com.gargdental.excelcomparator",
    )
