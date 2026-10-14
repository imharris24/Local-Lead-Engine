# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build specification for Local Lead Engine.

Builds a single-file Windows executable:
    pyinstaller build.spec

The output .exe will be in dist/ — no Python installation required.
"""

import sys
from pathlib import Path

# Project root (where this .spec file lives)
PROJECT_ROOT = Path(SPECPATH).resolve()

# ---------------------------------------------------------------------------
# Data files to bundle
# ---------------------------------------------------------------------------
datas = []

# ---------------------------------------------------------------------------
# Hidden imports (libraries PyInstaller may not detect automatically)
# ---------------------------------------------------------------------------
hiddenimports = [
    "playwright",
    "playwright.sync_api",
    "yaml",
    "customtkinter",
    # Ensure all submodules are included
    "app",
    "app.config",
    "app.database.connection",
    "app.database.models",
    "app.database.repository",
    "app.scraper.browser",
    "app.scraper.business",
    "app.scraper.parser",
    "app.scraper.search",
    "app.processing.normalizer",
    "app.processing.deduplicator",
    "app.processing.validator",
    "app.export.csv_exporter",
    "app.logging",
    "gui",
    "gui.app",
]

# ---------------------------------------------------------------------------
# Binaries to include (Playwright's Chromium driver if present locally)
# ---------------------------------------------------------------------------
binaries = []

# Try to include Playwright browsers if they exist in the default location
playwright_browsers = Path.home() / "AppData" / "Local" / "ms-playwright"
if playwright_browsers.exists():
    binaries.append((str(playwright_browsers), "ms-playwright"))

# ---------------------------------------------------------------------------
# Build configuration
# ---------------------------------------------------------------------------
a = Analysis(
    [str(PROJECT_ROOT / "gui" / "app.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "pytest",          # testing framework — not needed at runtime
        "tkinter.test",    # tkinter test modules
        "unittest",
        "pydoc",
        "doctest",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="LeadEngine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                # compress the binary (may not be available)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # no console window — pure GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon=str(PROJECT_ROOT / "assets" / "icon.ico"),  # uncomment if you have an icon
    # version=str(PROJECT_ROOT / "assets" / "version.txt"),  # uncomment for version info
)
