"""SCBE shim — Python mirror of services/scbe-shim (Cloudflare Worker)."""
from .patterns import match_auditor_phrasing  # noqa: F401
from .axioms import evaluate_axioms  # noqa: F401
from .decision import decide  # noqa: F401
