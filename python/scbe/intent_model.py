"""Compatibility shim -- the canonical injection classifier now ships in the package.

All logic lives in ``src/scbe_aethermoore/intent_model.py`` (single source: it must live
under ``src/`` to ship in the wheel, and the gate -- both the reference CLI via
``scbe_aethermoore._intent_screen`` and ``scbe_aethermoore.scan`` -- loads it from there).
This module re-exports it so any path-based or legacy reference keeps working without a
second copy that could drift.
"""

from __future__ import annotations

import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from scbe_aethermoore.intent_model import (  # noqa: E402,F401
    DEFAULT_MODEL,
    configured_model,
    injection_prob,
    is_available,
)
