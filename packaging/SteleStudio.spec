# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Stele Studio — one-file console executable.

Build via the helper script (recommended):
    python packaging/build_app.py --onefile

Or directly with PyInstaller:
    pyinstaller packaging/SteleStudio.spec

The executable behaves like `python -m stele`:
    SteleStudio                     # start Studio, open browser
    SteleStudio --no-browser        # start without opening browser
    SteleStudio --port 8080         # custom port
    SteleStudio --help              # usage
"""
from pathlib import Path

# SPECPATH is the directory containing this spec file (i.e. packaging/).
# ROOT is the project root one level up.
ROOT = Path(SPECPATH).parent

a = Analysis(
    [str(ROOT / 'stele' / '__main__.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # webapp assets are placed at stele/webapp/ inside the bundle so that
        # the frozen HERE path in web.py resolves them correctly.
        (str(ROOT / 'stele' / 'webapp'), 'stele/webapp'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Trim unused stdlib heavyweights to keep the bundle lean.
    excludes=['tkinter', 'unittest', 'distutils', 'test', 'lib2to3'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SteleStudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
