# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the standalone `scbe` CLI — one self-contained binary per
# platform (no Python install needed).  Build:  pyinstaller scbe.spec
# Bundles the data the cube system loads at import: the 18-language dialect table +
# python/scbe data dir (collect_data_files) and the root schemas/ dir (ingestion_rights
# validates against it at import). Cross-platform: datas are (src, dest) tuples.
import os
import sys

# Put THIS repo at the front of the build-time import path before anything is collected.
#
# collect_data_files()/collect_submodules() resolve a package by importing it with the
# build interpreter, so they follow whatever sys.path happens to be. The package here is
# named `python`, which is the worst possible name to leave to path order: on the macOS
# runner the interpreter is a Framework build rooted at
# /Library/Frameworks/Python.framework/Versions/3.12/, whose own shared library is a file
# literally named `Python`, and macOS filesystems are case-insensitive by default. `python`
# resolved to something that was not this repo, PyInstaller logged
# "skipping data collection for module 'python.scbe' as it is not a package", and the
# resulting binary died at startup with `No module named 'python.scbe'` -- while Windows and
# Linux, being case-sensitive, built the same spec correctly.
#
# Prepending the repo root removes the ambiguity at the only point where it matters. The
# real cure is to stop shipping a top-level package called `python` at all, but that is a
# breaking change to a public import path and belongs in a major version.
sys.path.insert(0, os.path.abspath(os.getcwd()))

from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_submodules


def modules_under(pkg_dir, pkg_name):
    """Enumerate submodules from the FILESYSTEM rather than the import system.

    collect_submodules() has to import the parent package to walk it, and resolving
    `python` went wrong on macOS: the filesystem is case-insensitive, so a lookup for
    `python` can match the interpreter's own `Python` directory in the hosted tool cache
    instead of this repo's `python/`. The build then succeeded while silently freezing in
    nothing, and the binary died on first run with `No module named 'python.scbe'`.

    Walking the directory cannot be misdirected that way — it names exactly the files that
    are here. Kept alongside collect_submodules (below) rather than replacing it, so the
    two disagreeing can only ever ADD modules, never drop them.
    """
    found = []
    for root, _dirs, files in os.walk(pkg_dir):
        rel = os.path.relpath(root, pkg_dir)
        prefix = pkg_name if rel == os.curdir else pkg_name + "." + rel.replace(os.sep, ".")
        if not os.path.exists(os.path.join(root, "__init__.py")):
            continue
        found.append(prefix)
        for f in files:
            if f.endswith(".py") and f != "__init__.py":
                found.append(prefix + "." + f[:-3])
    return found


datas = [('schemas', 'schemas')]
hiddenimports = []
# `python/` now carries an __init__.py, so collect_data_files resolves it as a real package
# and picks up the 3 data files (polyglot_dialects.json + data/) it previously skipped with
# "not a package". Do NOT also add ('python/scbe', 'python/scbe') as a datas tree: that
# duplicates these destinations, and the macOS onefile extractor then aborts with
# "[PYI-1858:ERROR] Failed to create parent directory structure" because one entry wants
# python/scbe/data as a file path while the other wants it as a directory.
# Stage this package's data under a NEUTRAL prefix, never under 'python/'.
#
# collect_data_files('python.scbe') targets <_MEIPASS>/python/scbe/..., and the bundle root
# also holds the CPython shared library -- named exactly 'Python' for a macOS Framework
# build. macOS is case-insensitive by default, so a 'python' directory cannot coexist with a
# 'Python' file and the bootloader aborted before running anything:
#     [PYI-1903:ERROR] Failed to create parent directory structure.
# Case-sensitive Linux and Windows never saw it. python/scbe/_bundled_data.py knows about
# this prefix and is what the two load sites now go through.
for _src, _dst in collect_data_files('python.scbe'):
    _rel = os.path.relpath(_dst, os.path.join('python', 'scbe'))
    datas.append((_src, os.path.join('scbe_data', _rel) if _rel != os.curdir else 'scbe_data'))
hiddenimports += collect_submodules('python.scbe')
hiddenimports += modules_under(os.path.join('python', 'scbe'), 'python.scbe')
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
