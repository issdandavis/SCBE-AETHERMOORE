#!/usr/bin/env python3
"""Canonical entrypoint for the SCBE multi-swarm router.

`openclaw_swarm.py` remains as a compatibility entrypoint because earlier local
artifacts and docs referenced it. The system is broader than OpenClaw: OpenClaw
is one router/bootstrap surface among many possible free/local agent swarms.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_COMPAT_PATH = Path(__file__).with_name("openclaw_swarm.py")
_SPEC = importlib.util.spec_from_file_location("_scbe_swarm_router_impl", _COMPAT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"cannot load swarm router implementation from {_COMPAT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


if __name__ == "__main__":
    raise SystemExit(_MODULE.main())
