"""
SCBE HYDRA System
=================

"Many Heads, One Governed Body"

A universal AI armor that any AI can wear - Claude, Codex, GPT, local LLMs.
Terminal-native with multi-tab browser support and central ledger.

Components:
- HydraSpine: Central coordinator (terminal API)
- HydraHead: Interface for any AI to connect
- HydraLimb: Execution backends (browser, terminal, API)
- Librarian: Central ledger manager with cross-session memory
- Ledger: SQLite-based action/decision history

Usage:
    # Terminal pipe interface
    echo '{"action": "navigate", "url": "https://example.com"}' | hydra

    # Python API
    from hydra import HydraSpine
    spine = HydraSpine()
    await spine.execute({"action": "navigate", "url": "..."})

    # Any AI can wear the armor
    from hydra import HydraHead
    head = HydraHead(ai_type="claude", model="opus")
    await head.connect(spine)
"""

from .spine import HydraSpine
from .head import HydraHead
from .limbs import BrowserLimb, TerminalLimb, APILimb
from .librarian import Librarian
from .ledger import Ledger, LedgerEntry

__all__ = [
    "HydraSpine",
    "HydraHead",
    "BrowserLimb",
    "TerminalLimb",
    "APILimb",
    "Librarian",
    "Ledger",
    "LedgerEntry",
]

__version__ = "1.0.0"
