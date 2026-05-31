import sys
from pathlib import Path

# Make scbe_govern importable when pytest runs from the repo root
_pkg_root = Path(__file__).resolve().parents[1]
if str(_pkg_root) not in sys.path:
    sys.path.insert(0, str(_pkg_root))
