"""Session-level fixture: build the cross-language lookup artifact on demand.

`scripts/agents/scbe_code.py` reads
`artifacts/cross_language_lookup/full_cross_language_lookup.json` for its
lookup-mode commands. The artifacts/ tree is gitignored, so CI starts cold
and `_load_lookup` raises FileNotFoundError before the test can run.

The lookup is a deterministic compose of in-tree sources
(`src.crypto.sacred_tongues` + `src.ca_lexicon`), so we just regenerate it
once per session by importing the build script and calling its main().
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LOOKUP_PATH = REPO_ROOT / "artifacts" / "cross_language_lookup" / "full_cross_language_lookup.json"


@pytest.fixture(scope="session", autouse=True)
def _ensure_cross_language_lookup_artifact():
    if LOOKUP_PATH.exists():
        return
    builder = importlib.import_module("scripts.system.build_cross_language_lookup")
    saved_argv = sys.argv
    try:
        sys.argv = [builder.__file__]
        rc = builder.main()
    finally:
        sys.argv = saved_argv
    if rc != 0 or not LOOKUP_PATH.exists():
        pytest.skip(
            f"cross-language lookup builder returned rc={rc}; artifact at {LOOKUP_PATH} missing"
        )
