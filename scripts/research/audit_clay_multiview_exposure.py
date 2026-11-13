"""CLI for the independent Clay multi-view exposure auditor."""

from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.clay_multiview_exposure_audit import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
