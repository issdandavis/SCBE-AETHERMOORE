"""Make spiral-word-app importable for tests (the dir has a hyphen)."""

from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_APP_DIR = os.path.join(_REPO_ROOT, "spiral-word-app")
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)
