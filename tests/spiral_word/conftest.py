"""Make spiral-word-app importable for tests (the dir has a hyphen)."""

from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_APP_DIR = os.path.join(_REPO_ROOT, "spiral-word-app")
if _APP_DIR in sys.path:
    sys.path.remove(_APP_DIR)
sys.path.insert(0, _APP_DIR)
sys.modules.pop("governance", None)
