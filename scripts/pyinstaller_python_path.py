"""Keep the frozen ``python`` package importable beside macOS's ``Python`` library.

PyInstaller 6's path finder rejects paths that resolve to files. On a
case-insensitive filesystem, its virtual package path ``_MEIPASS/python``
resolves to the bundled shared library ``Python``. A trailing separator marks
the search path as a directory while preserving its relative PYZ package name.
The code stays in the archive; package data already lives under scbe_data/.
"""

import os
import sys

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    import python

    # Preserve a real search path, unlike the earlier empty-__path__ workaround.
    # Leave working paths alone on platforms without the filename collision.
    python.__path__[:] = [path + os.sep if os.path.isfile(path) else path for path in python.__path__]
