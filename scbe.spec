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

# scbe.py line ~67 does `from scbe_aethermoore import _intent_screen`, and that only
# resolves because line ~64 inserts REPO_ROOT/src into sys.path AT RUNTIME. PyInstaller's
# analysis is static and cannot follow a computed sys.path.insert, so with pathex=['.']
# it never discovered the package and never bundled it -- the built binary died on its
# first command with `ModuleNotFoundError: No module named 'scbe_aethermoore'`.
#
# The runtime shim cannot save it either: in a frozen app `Path(__file__).parent` is the
# extraction dir, so REPO_ROOT/src does not exist and the insert is a no-op. The package
# has to be frozen in as a real top-level module, which needs BOTH of these:
#   - 'src' on pathex, so Analysis can import it at build time
#   - collect_submodules, so lazily-imported submodules come along
hiddenimports += collect_submodules('scbe_aethermoore')


a = Analysis(
    ['scbe.py'],
    pathex=['.', 'src'],
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
