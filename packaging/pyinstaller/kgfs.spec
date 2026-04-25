# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for KG File Search.

Build with:
    python scripts/build_package.py --clean

The default mode is onedir. `scripts/build_package.py --mode onefile` sets
KGFS_PYINSTALLER_MODE=onefile for an experimental onefile executable.
"""

from __future__ import annotations

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

ROOT = Path(SPECPATH).resolve().parents[1]
MODE = os.environ.get("KGFS_PYINSTALLER_MODE", "onedir")
PACKAGE_NAME = os.environ.get("KGFS_PACKAGE_NAME", "KGFS")

datas = [
    (str(ROOT / "kgfs" / "web" / "templates"), "kgfs/web/templates"),
    (str(ROOT / "kgfs" / "web" / "static"), "kgfs/web/static"),
    (str(ROOT / "config.example.yaml"), "."),
    (str(ROOT / "README.md"), "."),
    (str(ROOT / "LICENSE"), "."),
]

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan.on",
]
hiddenimports += collect_submodules("pypdf")

excludes = [
    "tests",
    "pytest",
    "pytest_mock",
    "sentence_transformers",
    "transformers",
    "torch",
    "tensorflow",
    "openai",
    "sqlite_vec",
    "hnswlib",
    "faiss",
    "numpy",
]

a = Analysis(
    [str(ROOT / "kgfs" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if MODE == "onefile":
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name="kgfs",
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
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="kgfs",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=True,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name=PACKAGE_NAME,
    )
