"""Health scan conftest — ensures src/ modules are importable."""
import sys
import os
from pathlib import Path

# Force src/ to front of sys.path before any other conftest runs
_src = str(Path(__file__).resolve().parent.parent.parent / "src")
if _src in sys.path:
    sys.path.remove(_src)
sys.path.insert(0, _src)

# Pre-import the src/ variant so Python caches it correctly
import importlib
for mod_path in [
    "symphonic_cipher.scbe_aethermoore.governance",
    "symphonic_cipher.scbe_aethermoore.governance.grand_unified",
    "symphonic_cipher.scbe_aethermoore.trinary",
    "symphonic_cipher.scbe_aethermoore.negabinary",
    "symphonic_cipher.scbe_aethermoore.flock_shepherd",
]:
    try:
        importlib.import_module(mod_path)
    except Exception:
        pass
