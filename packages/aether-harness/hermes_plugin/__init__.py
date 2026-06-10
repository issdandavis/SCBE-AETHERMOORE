"""Hermes plugin package: SCBE governance seam (in-repo, reproducible).

The harness engine (Hermes) is vendored *by reference* (see
`../vendor/hermes/VENDORED.md`): bootstrap clones the pinned upstream commit and
applies our patch. This directory is the only governance-specific code that gets
installed into the engine's plugin dir, so it lives in-repo and is bootstrapped
into the clone rather than committed as part of a 127 MB source dump.

The real adapter is `scbe_governance_plugin` (one level up); this `__init__`
just makes it importable as a Hermes bundled plugin and re-exports `register`.
"""

import sys
from pathlib import Path

# scbe_governance_plugin.py + governance_seam.py live in the package root, one
# directory above this plugin folder.
_PKG = Path(__file__).resolve().parents[1]
if str(_PKG) not in sys.path:
    sys.path.insert(0, str(_PKG))

from scbe_governance_plugin import register  # noqa: F401,E402
