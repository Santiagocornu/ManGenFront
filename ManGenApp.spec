# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files
import os

# Collect flet package data (includes controls/material/icons.json)
datas = collect_data_files('flet')

# Include project assets (logo.ico, logo.png, etc.) so they are available at runtime
assets_dir = os.path.join(os.path.abspath('.'), 'assets')
if os.path.isdir(assets_dir):
    for fn in os.listdir(assets_dir):
        src = os.path.join(assets_dir, fn)
        if os.path.isfile(src):
            # copy each asset into the bundled 'assets' folder
            datas.append((src, 'assets'))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='ManGenApp',
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
    icon=['assets\\logo.ico'],
)
