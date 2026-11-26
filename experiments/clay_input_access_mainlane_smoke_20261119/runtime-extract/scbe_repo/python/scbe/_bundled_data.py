"""Locate this package's data files, including inside a PyInstaller onefile binary.

Normally `Path(__file__).parent` is right. In a frozen build it is not, and on macOS it is
actively fatal.

PyInstaller extracts bundled data under `sys._MEIPASS`, so data for this package would land
in `<_MEIPASS>/python/scbe/`. But the bundle root also contains the CPython shared library,
and for a macOS Framework build that library is a file named exactly `Python`. macOS
filesystems are case-insensitive by default, so creating a directory `python` alongside a
file `Python` is impossible -- the bootloader aborted before any of our code ran:

    [PYI-1903:ERROR] Failed to create parent directory structure.

Linux and Windows are case-sensitive and never noticed. So the frozen build stages this
package's data under a neutral `scbe_data/` prefix instead (see scbe.spec), and this helper
is what knows about the two layouts. Source checkouts are completely unaffected.

The real cure is to stop shipping a top-level package named `python` at all; that is a
breaking change to a public import path and belongs in a major version.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Must match the destination prefix used in scbe.spec.
FROZEN_PREFIX = "scbe_data"


def data_root() -> Path:
    """Directory that stands in for `python/scbe/` when looking up bundled data files."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / FROZEN_PREFIX
    return Path(__file__).resolve().parent


def data_path(*parts: str) -> Path:
    """Path to a data file shipped with this package, e.g. data_path('data', 'x.csv')."""
    return data_root().joinpath(*parts)
