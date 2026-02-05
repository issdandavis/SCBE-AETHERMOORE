"""
SCBE HYDRA System
=================

"Many Heads, One Governed Body"

A universal AI armor that any AI can wear - Claude, Codex, GPT, local LLMs.
Terminal-native with multi-tab browser support and central ledger.

Research Validation:
- SentinelAgent (2025) - Graph Fourier anomaly detection
- ML-KEM/ML-DSA (FIPS 203/204) - Quantum-resistant crypto
- SwarmRaft (2025) - Byzantine consensus f<n/3
- Spectral Regularization (2024) - Adversarial robustness

Components:
- HydraSpine: Central coordinator (terminal API)
- HydraHead: Interface for any AI to connect
- HydraLimb: Execution backends (browser, terminal, API)
- Librarian: Central ledger manager with cross-session memory
- Ledger: SQLite-based action/decision history
- Spectral: Graph Fourier analysis for anomaly detection
- Consensus: Byzantine fault-tolerant voting

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

    # Run spectral analysis
    from hydra import GraphFourierAnalyzer, analyze_hydra_system
    gfss = GraphFourierAnalyzer()
    anomalies = await analyze_hydra_system(librarian, gfss)

    # Byzantine consensus
    from hydra import ByzantineConsensus, RoundtableConsensus
    consensus = RoundtableConsensus()
    result = await consensus.roundtable_consensus(...)
"""

from .spine import HydraSpine
from .head import HydraHead, create_claude_head, create_codex_head, create_gpt_head
from .limbs import BrowserLimb, TerminalLimb, APILimb, MultiTabBrowserLimb
from .librarian import Librarian, MemoryQuery, MemoryResult
from .ledger import Ledger, LedgerEntry, EntryType
from .spectral import (
    GraphFourierAnalyzer,
    ByzantineDetector,
    SpectralAnomaly,
    analyze_hydra_system
)
from .consensus import (
    ByzantineConsensus,
    RoundtableConsensus,
    Vote,
    Proposal,
    ConsensusResult,
    VoteDecision
)
from .websocket_manager import (
    WebSocketManager,
    WebSocketClient,
    SubscriptionChannel,
    ClientState,
    create_websocket_manager,
    run_websocket_server
)

__all__ = [
    # Core
    "HydraSpine",
    "HydraHead",
    "create_claude_head",
    "create_codex_head",
    "create_gpt_head",
    # Limbs
    "BrowserLimb",
    "TerminalLimb",
    "APILimb",
    "MultiTabBrowserLimb",
    # Memory
    "Librarian",
    "MemoryQuery",
    "MemoryResult",
    "Ledger",
    "LedgerEntry",
    "EntryType",
    # Spectral Analysis (GFSS)
    "GraphFourierAnalyzer",
    "ByzantineDetector",
    "SpectralAnomaly",
    "analyze_hydra_system",
    # Consensus
    "ByzantineConsensus",
    "RoundtableConsensus",
    "Vote",
    "Proposal",
    "ConsensusResult",
    "VoteDecision",
    # WebSocket (Phase 1 Q2 2026)
    "WebSocketManager",
    "WebSocketClient",
    "SubscriptionChannel",
    "ClientState",
    "create_websocket_manager",
    "run_websocket_server",
]

__version__ = "1.2.0"
