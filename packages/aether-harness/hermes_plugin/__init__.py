"""Hermes plugin package: SCBE governance seam (in-repo, reproducible).

The harness engine (Hermes) is vendored *by reference* (see
`../vendor/hermes/VENDORED.md`): bootstrap clones the pinned upstream commit and
applies our patch. This directory is the only governance-specific code that gets
installed into the engine's plugin dir, so it lives in-repo and is bootstrapped
into the clone rather than committed as part of a 127 MB source dump.

The real adapter is `scbe_governance_plugin` (it lives in the package root,
alongside `governance_seam.py`). This `__init__` only has to make that module
importable and re-export `register`.

The same file is used in two places — imported in-place from the package, and
COPIED into the engine's `plugins/scbe-governance/`. So it must locate the
package root robustly instead of assuming a fixed relative depth:

    1. `import scbe_governance_plugin` directly (works if bootstrap dropped an
       `aether_harness.pth` into the venv, or the package is otherwise on path);
    2. else try `AETHER_HARNESS_PKG` (bootstrap can export the absolute path);
    3. else try `parents[1]` (true only when imported in-place from the package);
    4. else walk a few likely roots looking for `scbe_governance_plugin.py`.
"""

import os
import sys
from pathlib import Path


def _load_register():
    try:  # 1. already importable (venv .pth, installed, or in-place)
        from scbe_governance_plugin import register  # type: ignore

        return register
    except Exception:
        pass

    candidates = []
    env = os.environ.get("AETHER_HARNESS_PKG")
    if env:
        candidates.append(Path(env))
    here = Path(__file__).resolve()
    candidates.append(here.parents[1])  # in-place: packages/aether-harness/
    # Fallback search roots (covers the copied-into-clone case where the package
    # is not adjacent): the user's repo checkout under a few common layouts.
    candidates += [
        Path.home() / "SCBE-AETHERMOORE" / "packages" / "aether-harness",
    ]

    for pkg in candidates:
        if (pkg / "scbe_governance_plugin.py").is_file():
            if str(pkg) not in sys.path:
                sys.path.insert(0, str(pkg))
            from scbe_governance_plugin import register  # type: ignore

            return register

    raise ImportError(
        "scbe-governance plugin: could not locate scbe_governance_plugin.py. "
        "Set AETHER_HARNESS_PKG to the packages/aether-harness path."
    )


register = _load_register()
