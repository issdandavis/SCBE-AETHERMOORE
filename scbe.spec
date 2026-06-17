# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the standalone `scbe` CLI — one self-contained binary per
# platform (no Python install needed).  Build:  pyinstaller scbe.spec
# Bundles the data the cube system loads at import: the 18-language dialect table +
# python/scbe data dir (collect_data_files) and the root schemas/ dir (ingestion_rights
# validates against it at import). Cross-platform: datas are (src, dest) tuples.
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_submodules

datas = [('schemas', 'schemas')]
hiddenimports = []
datas += collect_data_files('python.scbe')
hiddenimports += collect_submodules('python.scbe')
hiddenimports += collect_submodules('src.crypto')


a = Analysis(
    ['scbe.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'torch', 'tensorflow'],
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
    name='scbe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
