# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for backend server
"""

import sys
from pathlib import Path

# Project root is where this spec file is located
project_root = Path(SPECPATH)
backend_dir = project_root / 'backend'

a = Analysis(
    [str(backend_dir / 'app' / 'main.py')],
    pathex=[str(backend_dir)],
    binaries=[],
    datas=[
        (str(backend_dir / 'data'), 'data'),
        (str(backend_dir / 'app' / 'data'), 'app/data'),
    ],
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='sanguo-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False to hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
