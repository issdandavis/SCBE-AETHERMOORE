from __future__ import annotations

import importlib.util
from pathlib import Path


_MODULE_PATH = Path(__file__).with_name("scbe-system-cli.py")
_SPEC = importlib.util.spec_from_file_location("scbe_system_cli_runtime", _MODULE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load SCBE system CLI from {_MODULE_PATH}")

_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

main = _MODULE.main
build_parser = _MODULE.build_parser


if __name__ == "__main__":
    raise SystemExit(main())
